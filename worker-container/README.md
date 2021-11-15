to build, execute:
```
docker image build --build-arg POOL_PASSWORD=<enter pw here>  -t img_name . 
```

to run, execute:
```
docker container run \
    --cpus=1 \
    -e MACHINE_SPECIAL_ID=<enter id here> \
    -e CNODOR_HOST=<enter host of central manager> \
    -e NUM_CPUS=1 \
    img_name
```

`MACHINE_SPECIAL_ID` is an attribute that will be set in the machine classad.
This will allow us to set a requirement for a job that the given s.t. the job
matches (lands on) the machine with the id.

to build all, execute:
```
./build-all.sh
```
