#!/usr/bin/env python3
import os
import time
import sys
import shutil
import enum
import signal
import argparse
import threading
import pickle
import uuid

from collections import namedtuple
from datetime import datetime
from pathlib import Path
from typing import Dict, Set

import docker
import paramiko

import htcondor
import classad

from htcondor import dags 

# custom attribute we will use to specify arch 
ARCH_CUSTOM_ATTRIBUTE = "REQUIRED_ARCH"

def print_red(s): 
    print("\033[91m {}\033[00m" .format(s))
def print_green(s): 
    print("\033[92m {}\033[00m" .format(s))
def print_cyan(s): 
    print("\033[96m {}\033[00m" .format(s))

class JobStatus(enum.Enum):
    UNEXPANDED = 0
    IDLE = 1
    RUNNING = 2
    REMOVED = 3
    COMPLETED = 4
    HELD = 5
    SUBMISSION_ERR = 6

class Arch(enum.Enum):
    X86_64 = "X86_64"
    AARCH64 = "AARCH64"

def get_available_slots(col: htcondor.Collector) -> Dict:
    """
    A a dict of available slots per architecture in the format:

    {
        "X86_64": <int>,
        "AARCH64": <int>,
        "other": <int>,
        "unavailable": <int>
    }


    :param col: collector to query
    :type col: htcondor.Collector
    :return: dict of available/unavailable slots
    :rtype: Dict
    """

    result = {
        Arch.X86_64.value: 0,
        Arch.AARCH64.value: 0,
        "other": 0,
        "unavailable": 0
    }

    num_total_available = 0
    
    slots = col.query(
        htcondor.AdTypes.Startd,
        projection=["Name", "Activity", "State", "Arch"]
    )

    for s in slots:
        arch = s["Arch"]
        state = s["State"]
        activity = s["Activity"]

        if state == "Unclaimed" and activity == "Idle":
            if arch in result:
                result[arch] += 1
            else:
                result["other"] += 1
            
            num_total_available += 1
        else:
            result["unavailable"] += 1
    
    return result

class QueueState:
    class Count:
        def __init__(self):
            self.idle = 0
            self.running = 0

        def __repr__(self):
            return "Count(idle={}, running={})".format(self.idle, self.running)

    def __init__(self):
        self.X86_64 = self.Count()
        self.AARCH64 = self.Count()

    def __str__(self):
        return "QueueState: X86_64={}, AARCH64={}".format(self.X86_64, self.AARCH64)

class PoolState:
    def __init__(self):
        # number of X86_64 slots available
        self.X86_64 = 0
        # number of AARCH64 slots available
        self.AARCH64 = 0
        # total number of unavailable slots
        self.unavailable = 0

    def __str__(self):
        return "PoolState: X86_64={}, AARCH64={}, unavailable={}".format(
                self.X86_64,
                self.AARCH64,
                self.unavailable
            )

EstimatedLoad = namedtuple("EstimatedLoad", [Arch.X86_64.value, Arch.AARCH64.value])

class SSHClient:
    def __init__(self):
        self.client = paramiko.SSHClient()
        self.client.load_system_host_keys()

    def execute(self, cmd: str) -> dict:
        try:
            client.connect(
                        hostname="scitech-rpi-1.ads.isi.edu",
                        username="scitech",
                        key_filename="/Users/ryantanaka/.ssh/edge-no-pw"
                    )

            stdin, stdout, stderr = client.exec_command(cmd)
            exit_code = stdout.channel.recv_exit_status()
            if exit_code != 0:
                raise RuntimeError

            for line in stdout:
                print(line)

        except paramiko.SSHException as e:
            print(e)
        except RuntimeError:
            print("SSH command: {} FAILED with exit_code: {}".format(cmd, exit_code))
            print("stder:")
            for line in stderr:
                print(line.strip())
        finally:
            client.close()

        return {
                    "exit_code": exit_code,
                    "stdin": stdin,
                    "stdout": stdout,
                    "stderr": stderr,
                }

class Provisioner:
    def __init__(self, condor_host: str = None, token_dir: str = None):
        self.condor_host = condor_host
        self.token_dir = token_dir
        
        self.docker = docker.from_env()
        self.ssh_client = SSHClient()
        
        '''
        {
            "<id>": {
                "cont": <cont obj>,
                "last_idle": <datetime>
            },
            ...
        }
        '''
        self.containers = dict()
        self.containers[Arch.X86_64.value] = dict()
        self.containers[Arch.AARCH64.value] = dict()


        self.collector = htcondor.Collector()
        self.schedd_ad = self.collector.locate(htcondor.DaemonTypes.Schedd)
        self.schedd = htcondor.Schedd(self.schedd_ad)

        self.lock = threading.Lock()

        self.stop_event = threading.Event()

    ### Workload/Pool State ####################################################
    def get_queue_state(self) -> QueueState:
        """
        Current state of the queue. Returns number of idle and running jobs for
        x86_64 and ARM

        :return: number of idle and running jobs 
        :rtype: Provisioner.QueueState
        """

        # this doesn't account for for all jobs, only the ones for which we have
        # set the custom attribute: REQUIRED_ARCH
        result = QueueState()

        for job in self.schedd.xquery(projection=["ClusterId", "ProcId", "JobStatus", ARCH_CUSTOM_ATTRIBUTE]):
            required_arch = str(job.get(ARCH_CUSTOM_ATTRIBUTE))
            job_status = job["JobStatus"]

            if required_arch == Arch.X86_64.value:
                if job_status == JobStatus.IDLE.value: 
                    result.X86_64.idle += 1
                elif job_status == JobStatus.RUNNING.value:
                    result.X86_64.running += 1

            elif required_arch == Arch.AARCH64.value:
                if job_status == JobStatus.IDLE.value:
                    result.AARCH64.idle += 1
                elif job_status == JobStatus.RUNNING.value:
                    result.AARCH64.running += 1

        return result

    
    def get_pool_state(self) -> PoolState:
        """
        Get the count of available and unvailable slots per architecture.

        :raises RuntimeError: encountered unexpected arch
        :return: current state of the pool 
        :rtype: Provisioner.PoolState
        """

        # THIS DOESN"T ACCOUNT FOR DYNAMIC SLOTS>........
        result = PoolState()
        
        slots = self.collector.query(
            htcondor.AdTypes.Startd,
            projection=["Name", "Activity", "State", "Arch", "DEMO_NODE"]
        )

        for s in slots:
            arch = s["Arch"]
            state = s["State"]
            activity = s["Activity"]
            is_demo_node = s.get("DEMO_NODE")

            # only care about workers in the pool that are part of this demo
            if is_demo_node:
                if state == "Unclaimed" and activity == "Idle":
                    if arch == Arch.X86_64.value:
                        result.X86_64 += 1
                    elif arch == Arch.AARCH64.value:
                        result.AARCH64 += 1
                    else:
                        raise RuntimeError("did not expect arch: {}".format(arch))
                else:
                    result.unavailable += 1
        
        return result

    def get_idle_workers(self) -> Set[str]:
        """Return names of all the unclaimed idle workers

        :return: names of all unclaimed idle workers
        :rtype: Set[str]
        """
        idle_workers = set()
        
        slots = self.collector.query(
            htcondor.AdTypes.Startd,
            projection=["Name", "Activity", "State", "Arch", "DEMO_NODE"]
        )

        for s in slots:
            name = s["Name"]
            state = s["State"]
            activity = s["Activity"]
            is_demo_node = s.get("DEMO_NODE")

            if is_demo_node:
                if state == "Unclaimed" and activity == "Idle":
                    idle_workers.add(name)       

        return idle_workers


    def compute_load(self) -> EstimatedLoad:
        """
        Compute estimated load, calculated as 
        (num idle jobs of a given architechture / num unclaimed idle workers of the same arch)

        :return: load for x86_64 and aarch64
        :rtype: EstimatedLoad
        """
        queue_state = self.get_queue_state()
        pool_state = self.get_pool_state()

        print(queue_state)
        print(pool_state)

        if queue_state.X86_64.idle == 0 and pool_state.X86_64 == 0:
            x86_64_est_load = 0
        elif queue_state.X86_64.idle > 0 and pool_state.X86_64 == 0:
            x86_64_est_load = float("inf")
        else:
            x86_64_est_load = queue_state.X86_64.idle / pool_state.X86_64
        
        if queue_state.AARCH64.idle == 0 and pool_state.AARCH64 == 0:
            arm_est_load = 0
        elif queue_state.AARCH64.idle > 0 and pool_state.AARCH64 == 0:
            arm_est_load = float("inf")
        else:
            arm_est_load = queue_state.AARCH64.idle / pool_state.AARCH64

        return EstimatedLoad(
            X86_64=x86_64_est_load,
            AARCH64=arm_est_load
        )

    ### Container Management ###################################################
    def stop_containers(self):
        """
        To be run as a thread, stop_containers will check the pool state and
        currently managed containers to see if they have been sitting idle for
        too long. If they have been sitting idle for more than MAX_IDLE_DUR, the
        container will be killed via SIGINT.
        """

        print("stop_containers thread started")

        # if this is increased, calculated idle duration can start to become
        # inaccurate due race conditions from polling the queue
        POLLING_RATE = 1

        # if a worker has sat idle for longer than MAX_IDLE_DUR seconds, 
        # we will kill that container
        MAX_IDLE_DUR = 30


        while not self.stop_event.is_set():
            idle_workers = self.get_idle_workers()

            to_delete = list()
            for _id, value in self.containers[Arch.X86_64].items():
                # need to truncate id to be the same length as slot name
                # .... not great, but it will work for now so we can use fast
                # access of the set 
                if _id[:12] in idle_workers:
                    # if now - last_idle > MAX_IDLE_DUR then we kill
                    idle_dur = (datetime.now() - value["last_idle"]).total_seconds()                   

                    if idle_dur > MAX_IDLE_DUR:
                        print_red("STOPPING X86_64 cont {} (idle for {} seconds) sending SIGINT".format(_id, idle_dur))
                        with self.lock:
                            value["cont"].kill(signal=signal.SIGINT)
                        
                        to_delete.append(_id)
                            
                else:
                    # reset last_idle to now
                    with self.lock:
                        value["last_idle"] = datetime.now()

            for _id, last_idle in self.containers[Arch.AARCH64].items():
                if _id in idle_workers:
                    idle_dur = (datetime.now() - last_idle).total_seconds()

                    if idle_dur > MAX_IDLE_DUR:
                        print_red("STOPPING AARCH64 cont {} (idle for {} seconds) sending SIGINT".format(_id, idle_dur))
                        
                        result = self.ssh_client.execute("docker kill --signal=SIGINT {}".format(cont_id))
                        if result["exit_code"] != 0:
                            raise RuntimeError("ERROR SSH docker could not kill AARCH64 cont {}".format(cont_id))
                       
                        to_delete.append(cont_id)

            for _id in to_delete:
                del self.containers[_id]

            time.sleep(POLLING_RATE)

        print("stop_containers exiting")        

    def shutdown_all_containers(self):
        """Shutdown all running containers."""

        for _id, value in self.containers[Arch.X86_64.value].items():
            print("shutting down container {}".format(_id))
            value["cont"].kill(signal=signal.SIGINT)

        for cont_id in self.containers[Arch.AARCH64.value]:
            result = self.ssh_client.execute("docker kill --signal=SIGINT {}".format(cont_id))
            print("shutting down container {}".format(cont_id))
            if result["exit_code"] != 0:
                print("ERROR SSH docker could not kill {}".format(cont_id))

    def start_containers(self, rate: int, load_threshold: float):
        """
        Start containers to meet expected demand for workers based on 
        idle jobs in the queue.

        :param rate: polling rate
        :type rate: int
        :param load_threshold: threshold, which if exceeded, will cause a container to be created
        :type load_threshold: float
        :raises NotImplementedError: AARCH64 worker supported not added yet 
        """
        print("start_containers thread started")
        while not self.stop_event.is_set():
            load = self.compute_load()
            print_cyan("CURRENT LOAD: {}".format(load))


            if load.X86_64 > load_threshold:
                # start cont
                cont = self.docker.containers.run(
                    image="ryantanaka/condor9-x86_64-isi-demo-worker",
                    volumes=["/local-scratch/tanaka/condorexec/secrets:/root/secrets:ro"],
                    environment={"CONDOR_HOST":"workflow.isi.edu",},
                    remove=True,
                    detach=True  
                )

                print_green("STARTED {}".format(cont.id))
                with self.lock:
                    self.containers[Arch.X86_64.value][cont.id] = {
                        "cont": cont,
                        "last_idle": datetime.now()
                    }

            if load.AARCH64 > load_threshold:
                # start cont
                cont_name = str(uuid.uuid1())
                cmd = " ".join((
                        "abc",
                        "234"
                    ))

                result = self.ssh_client.execute(cmd)
                if result["exit_code"] == 0:
                    cmd = " ".join((
                            "docker",
                            "ps",
                            "-aqf",
                            "name={}".format(cont_name)
                        ))
                    result = self.ssh_client.execute(cmd)
                    cont_id = None
                    if result["exit_code"] == 0:
                        stdout = list(result["stdout"])
                        if len(stdout) > 0:
                            cont_id = stdout[0].strip()
                        else:
                            raise RuntimeError("SSH docker ps command could not get container id")
                    else:
                        raise RuntimeError("SSH docker ps command failed")

                    print_green("STARTED {}".format(cont_id))
                    with self.lock:
                        self.container[Arch.AARCH64][cont_id] = {
                                    "last_idle": datetime.now()
                                }
                else:
                    raise RuntimeError("SSH Docker command failed")
                

                raise NotImplementedError("still need to add AARCH64 worker")

            time.sleep(rate)
        
        print("start_containers exiting")

    def provision(self, rate: int, load_threshold: float):
        """
        Main provisioning function

        :param rate: rate (in seconds), at which to check if new containers need to be started
        :type rate: int
        :param load_threshold: threshold, which if exceeded, will cause a container to be created
        :type load_threshold: float
        """
        starter = threading.Thread(target=self.start_containers, args=(rate, load_threshold,))
        stopper = threading.Thread(target=self.stop_containers)

        starter.start()
        stopper.start()

        starter.join()
        stopper.join()

    ### Monitoring #############################################################
    def monitor(self, rate: int):
        slots_str = "{0:>20} {1} {2}"
        bar = "{} ".format(chr(9605))
        data = {
            "ts": list(),
            "unavailable": list(),
            "idle_worker": list(),
            "idle_job": list(),
            "running_job": list()
        }

        while True:
            pool = self.get_pool_state()
            queue = self.get_queue_state()
            
            # print pool status information
            print("**** POOL *****************************")
            print(slots_str.format(Arch.X86_64.value, bar*pool.X86_64, pool.X86_64))
            print(slots_str.format(Arch.AARCH64.value, bar*pool.AARCH64, pool.AARCH64))
            print(slots_str.format("Unavailable", bar*pool.unavailable , pool.unavailable))

            # print queue status information
            print("**** JOBS *****************************")
            print(Arch.X86_64.value)
            print(slots_str.format("running", bar*queue.X86_64.running, queue.X86_64.running))
            print(slots_str.format("idle", bar*queue.X86_64.idle, queue.X86_64.idle))
            print(Arch.AARCH64.value)
            print(slots_str.format("running", bar*queue.AARCH64.running, queue.AARCH64.running))
            print(slots_str.format("idle", bar*queue.AARCH64.idle, queue.AARCH64.idle))


            data["ts"].append(datetime.now().timestamp())
            data["unavailable"].append(pool.unavailable)
            data["idle_worker"].append(pool.X86_64)
            data["idle_job"].append(queue.X86_64.idle)
            data["running_job"].append(queue.X86_64.running)

            with open("data.pkl", "wb") as f:
                pickle.dump(data, f)
            
            print(data)

            time.sleep(rate)
            os.system("clear")

def parse_args(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description="demo tools")

    subparsers = parser.add_subparsers(help="demo command to run")

    ### Monitor ##############################################################
    parser_monitor = subparsers.add_parser("monitor", help="monitor pool and queue")
    parser_monitor.set_defaults(cmd="monitor")
    parser_monitor.add_argument(
        "monitor_rate",
        type=int,
        default=None,
        choices=range(1, 300),
        metavar="[1,300]",
        help="rate, in seconds, at which to monitor condor_collector and schedd"
    )

    ### Provision ############################################################
    parser_provision = subparsers.add_parser("provision", help="start provisioner")
    parser_provision.set_defaults(cmd="provision")
    parser_provision.add_argument(
        "provision_rate",
        type=int,
        default=10,
        choices=range(1, 600),
        metavar="[1,600]",
        help="""rate, in seconds, at which to poll condor_collector and schedd 
        to decide if worker must be provisioned"""
    )

    parser_provision.add_argument(
        "load_threshold",
        type=float,
        default=1.0,
        metavar="(0.1, 10]",
        help="""threshold of (num_idle jobs of a given arch / available workers 
        of a given arch) at which a new worker container will be started"""
    )

class ServiceExit(Exception):
    """Custom exception to trigger clean shutdown."""
    pass

def sigint_handler(signum, frame):
    print("got interrupt, exiting")
    raise ServiceExit

if __name__=="__main__":
    signal.signal(signal.SIGINT, sigint_handler)

    args = parse_args()

    if args.cmd == "monitor":    
        try:
            Provisioner().monitor(args.monitor_rate)
        except ServiceExit:
            print("exiting monitoring")

    elif args.cmd == "provision":
        try:
            provisioner = Provisioner()
            provisioner.provision(args.provision_rate, args.load_threshold)
        except ServiceExit:
            provisioner.stop_event.set()
            provisioner.shutdown_all_containers()
    else:
        raise RuntimeError("unexpected cmd: {}".format(args.cmd))
