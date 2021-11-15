to build, execute:
```
docker image buld --build-arg POOL_PASSWORD=<enter pw here>  -t img_name . 
```

to run, execute:
```
docker container run -e MACHINE_SPECIAL_ID=<enter id here> img_name
```

`MACHINE_SPECIAL_ID` is an attribute that will be set in the machine classad.
This will allow us to set a requirement for a job that the given s.t. the job
matches (lands on) the machine with the id.

