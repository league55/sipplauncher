Developer Guide extends [User Guide](user_guide.md) with some information, which is relevant for:

- Sipplauncher developers and contributors
- Users, who wish to understand how Sipplauncher works under the hood

## 1. Initialization

1. **Set up signal handler**

    We need to perform proper cleanup in case if:

    - a user interrupts with CTRL+C
    - Sipplaucnher is terminated with any other signal

    Otherwise, we'll leave stray "dummy" interfaces and partially-configured DUT.

    Thus, we set up our signal handler.

    There is a tricky place in signal handling - we can't do much inside the signal handler.
    We can't even log a message, because sometimes it causes a deadlock.
    The details of this issue are described in `Signals.py`.

    To work around this issue - we set a global variable inside the signal handler.
    And later we check this variable from the main code.
    Therefore, we have *interruption points*, which are deadlock-free.

2. **Parse command-line arguments**

    To support [Command-line arguments](user_guide.md#command-line-arguments), we use the `argparse` library.

3. **Set up TLS session keys interception**

    To support [Decrypting Diffie-Hellman TLS traffic](user_guide.md#decrypting-tls-traffic), we include a 3rd-party library `sipplauncher/sslkeylog.c`.
    In `main.py` we set the environment variable `LD_PRELOAD`, which points to `sslkeylog.so`.

    When we launch a child SIPp application, Linux checks this environment variable and preloads `sslkeylog.so` before running SIPp.
    This library overwrites some methods in the standard OpenSSL library.
    This makes possible to intercept and log TLS session keys.

Then **Sipplauncher** passes control to `Run.run()`, which is defined at `Run.py`.

`Run.run()` runs in a single thread and performs the following steps:

---

## 2. SIPpTest list collection

`TestPool` instance, defined at `TestPool.py`, collects names of subfolders inside a [test suite folder](user_guide.md#test-suite-folder-layout).
The names of subfolders are considered the [Test](user_guide.md#tests) names.
Then `TestPool`:

1. Sorts test names in alphabetical order
2. Iterates over the test names.

During iterating, each test name is checked.
The [test](user_guide.md#tests) is skipped, if:

1. A test name matches the [Template folder](user_guide.md#templates) name.
2. The `--pattern-exclude` [command-line argument](user_guide.md#command-line-arguments) is specified and a test name matches it.
3. The `--pattern-only` [command-line argument](user_guide.md#command-line-arguments) is specified and a test name doesn't match it.

If the [test](user_guide.md#tests) isn't skipped, a `SIPpTest` is instantiated from a test name and the instance is added to the list.
A `SIPpTest` instance, defined at `Test.py`, encapsulates everything, needed to execute the [test](user_guide.md#tests).

A list of `SIPpTest` instances, sorted alphabetically by the test name, is returned to `Run.run()`.

---

## 3. SIPpTest list processing

Then the `--group` [command-line argument](user_guide.md#optional-arguments) is considered.

`Run.run()` takes a slice of `SIPpTests`, which consists of a `--group` of elements, from the beginning of a `SIPpTest` list.
This slice is considered a `SIPpTest` run group.
Then `Run.run()` [processes](#4-sipptest-run-group-processing) a `SIPpTest` run group.

Then `Run.run()` takes the next slice from the `SIPpTest` list and [processes it](#4-sipptest-run-group-processing).

This repeats until all `SIPpTests` from the list are processed.

---

## 4. SIPpTest run group processing

`SIPpTest` run group processing could be divided into stages:

- consecutive stages [Pre-run](#pre-run) and [Post-run](#post-run): they're run in the context of the `Run.run()` thread.
- concurrent stage [Run](#run): it's run in the context of multiple spawned threads and processes.

Here is the order of these steps:

---

### 1. Pre-run

`Run.run()` consecutively iterates over `SIPpTests` in a run group.
For each of them, `SIPpTest.pre_run()` method is executed, which:

1. **Assigns dynamic IP addresses**

    The high-level overview is given in [Dynamically assigned IP address](user_guide.md#dynamic-ip-address-assignment).
    For a developer it's worth to add a few notes:

    1. The check if the randomly obtained address is already occupied, is performed through the [ARP ping](https://en.wikipedia.org/wiki/Arping).
    It's used instead of regular ICMP ping because some hosts in LAN might have ICMP replies disabled.
    And therefore, if we based on ICMP ping, we could cause Ethernet conflicts.
    The ARP ping is performed using the [Scapy](https://scapy.net/) library.

    2. A new "dummy" interface is created for each Test.
    Dummy interface is named with pattern `sipp-<test_run_id>`.
    Then the randomly generated IP addresses are assigned to the "dummy" interface.
    This way we do IP aliasing.
    We do the "dummy" interface approach instead of creating IP aliases via the `ip address add <addr> dev eth0` approach for the following reasons:

        1. to ease network cleanup: just destroy all interfaces which name matches the `sipp-<>` pattern
        2. to remove the need to specify or calculate network interface on which to create aliases: we rely on the Linux routing system

2. **Creates a test run folder**

    [Test run folder](user_guide.md#test-run-folder) is created by copying [Test](user_guide.md#tests) folder to location `/var/tmp/sipplaucnher/<test_name>/<test_run_id>`.

    Copying is performed using `shutil.copytree()`.

3. **Sets up logging into Test run folder**

    Sipplauncher [logging facilities](user_guide.md#log-files) and paths are configured in `/usr/local/etc/sipplauncher/sipplauncher.configlog.conf`.
    Static log location is by default defined there as `/tmp/sipplauncher.log`.

    We have following requirements:

    1. We need to easely separate the logs of different [Test](user_guide.md#tests) runs.
       Thus, we want to log the execution of each [Test](user_guide.md#tests) into a [Test run folder](user_guide.md#test-run-folder).
       The log path should look like `/var/tmp/sipplauncher/<test_name>/<test_run_id>/sipplauncher.log`, where `<test_run_id>` is random and isn't known beforehand.
       Therefore, the [Test](user_guide.md#tests) run log file location can't be static. It should be dynamic.

    2. We want to preserve the possibility to configure log message format in `/usr/local/etc/sipplauncher/sipplauncher.configlog.conf`.

    To fulfill the above requirements, we implement the logging class `sipplauncher.utils.Log.DynamicFileHandler`.
    It should be specified as a logging `class` for those logs, which need to be stored into a [Test run folder](user_guide.md#test-run-folder).

    At runtime, we check if the logging class is set to `sipplauncher.utils.Log.DynamicFileHandler`.
    And if yes, we supply an actual [Test run folder](user_guide.md#test-run-folder) path to `sipplauncher.utils.Log.DynamicFileHandler` instance.

4. **Replaces keywords using the Template Engine**

    A list of files, which need to be processed using the [Template engine](user_guide.md#template-engine), is collected:

    - [Scripts](user_guide.md#scripts): result of `glob.glob("*.sh")`.
    - [SIPp scenarios](user_guide.md#sipp-scenarios): the files, which match pattern `^(ua[cs]+)_(ua[0-9]+).xml$`.

    All these files are rendered by the [Jinja2](https://en.wikipedia.org/wiki/Jinja_(template_engine)) API `Template.render()`.

    If the rendering result differs from the original file content - the file is overwritten with the newly rendered content.

5. **Generates SSL certificates and keys**

    The process is described [here](user_guide.md#tls).
    Python `OpenSSL` library is used.

6. **Activates pcap sniffing**

    We use `scapy.sendrecv.AsyncSniffer` to start a new background thread.
    This thread installs the [BPF](https://en.wikipedia.org/wiki/Berkeley_Packet_Filter) on all system network interfaces.
    The BPF matches all traffic regarding [Dynamically assigned IP addresses](user_guide.md#dynamic-ip-address-assignment) for this particular [Test](user_guide.md#tests) run.
    The captured traffic is stored to the memory buffer.

---

### 2. **Run**

`Run.run()` iterates over `SIPpTests` in a run group and for each of them launches the `SIPpTest.run()` method in a dedicated Python `Thread`.

Then `Run.run()` waits for threads to finish.

`SIPpTest.run()` method performs following steps:

1. **Runs before.sh**

    If `before.sh` is present in a [Test run folder](user_guide.md#test-run-folder), we execute it with `subprocess.Popen()` API.

    Then we wait for it to finish and check its exit code.
    If the exit code is non-zero - we stop the test as FAILED.

2. **Forks a new PysippProcess**

    `PysippProcess` is a subclass of the `multiprocessing.Process`.

    `PysippProcess` performs `os.chdir()` to a [Test run folder](user_guide.md#test-run-folder) and launches SIPp through the API of the `Pysipp` library.

    We need to fork the `Process`, because we have the [requirement](user_guide.md#log-files) to store all the logs, which relate to [Test](user_guide.md#tests) run, in the [Test run folder](user_guide.md#test-run-folder).

    From this requirement we get the following outcome:

    1. Some of the SIPp log locations are not configurable and are logged to a current working directory.
       Therefore we need to `os.chdir()` into a [Test run folder](user_guide.md#test-run-folder) before running SIPp.
    2. `os.chdir()` changes the current working directory for a whole current process.
       However, we are going to use it inside the [concurrently running Threads](#2-run).
       Therefore, this introduces the race condition.
    3. Therefore, we need to launch a child `Process` from a `Thread`.
       And then, inside the child `Process`, call `os.chdir()` and then run SIPp.
       This way, we change the working directory inside the child process and avoid the race condition in the parent process.

3. **Reports test result**

    `SIPpTest.run()` waits for `PysippProcess` to finish.

    The test is reported as FAIL if `exitcode` is non-zero, SUCCESS otherwise.

    A `SIPpTest.run()` Thread measures time from its begging and reports the amount of time elapsed.

---

### 3. Post-run

Post-run performs a rollback of actions, which were done in the [Pre-run](#pre-run).
The rollback is performed in the opposite order of the [Pre-run](#pre-run).

`Run.run()` consecutively iterates over `SIPpTests` in a run group.
For each of them, `SIPpTest.post_run()` method is executed, which:

1. **Runs after.sh**

    If `after.sh` is present in a [Test run folder](user_guide.md#test-run-folder), we execute it with `subprocess.Popen()` API.

2. **Deactivates pcap sniffing**

    We invoke `scapy.sendrecv.AsyncSniffer.stop()` and wait until the background `Thread` terminates.

    Then we sort the memory buffer with pcap frames by the frame timestamp.
    This is needed, because in case if traffic goes through different network interfaces, it could appear in a slightly wrong order inside the memory buffer.

    Then we store the sorted memory buffer in file `sipp-<test_run_id>.pcap` in a [Test run folder](user_guide.md#test-run-folder).

3. **Removes a test run folder**

    We remove it with `shutil.rmtree()`, unless the `--leave-temp` [command-line argument](user_guide.md#command-line-arguments) was provided.

4. **Removes dynamic IP addresses**

    We remove a "dummy" pseudo-interface with name `sipp-<test_run_id>`.
