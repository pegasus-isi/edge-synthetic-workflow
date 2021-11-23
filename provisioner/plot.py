#!/usr/bin/env python3
import pickle

import matplotlib.pyplot as plt

with open("datapi.pkl", "rb") as f:
    d = pickle.load(f)

x = d["ts"]

# make time start from 0
x = [i - x[0] for i in x]

figs, axs = plt.subplots(2)
figs.suptitle("job queue and worker pool")

axs[0].plot(x, d["unavailable"], label="busy workers")
axs[0].plot(x, d["running_job"], label="running jobs")
axs[0].legend()
axs[0].set_ylim([0, 13])
axs[0].set_ylabel("count")

axs[1].plot(x, d["idle_worker"], label="idle workers")
axs[1].plot(x, d["idle_job"], label="idle jobs queued")
axs[1].legend()
axs[1].set_ylim([0, 13])
axs[1].set_ylabel("count")
axs[1].set_xlabel("time (seconds)")

plt.show()
