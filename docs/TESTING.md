# Testing

Run the dependency-free domain tests and Python compilation check:

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q app tests scripts
```

The eight tests cover password hashing, household-scoped query behavior and event fanout, multi-tab CSRF, child/display restrictions in the completion helper, exactly-once points accounting, and backup/restore. The production Docker image built successfully with `docker build`. HTTP tests could not run in this sandbox because creating a local listening socket is denied; `docker run` was rejected by Docker API permissions, and the Compose plugin is unavailable. Browser E2E, screenshots, physical iPhone tests, load tests, vulnerability scans and NAS resource measurements were not run. A sandbox that permits local sockets and container execution should add these checks before deployment.
