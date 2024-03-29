## Overview

- Sipplauncher accepts a path to a [test suite](#test-suite-folder-layout), which contains a set of subfolders - [tests](#tests).
- The [Test](#tests) subfolder should contain at least one [SIPp scenario](#sipp-scenarios).
- The [Test](#tests) subfolder may contain [scripts](#scripts) and other files.
- [Scripts](#scripts) and [SIPp scenarios](#sipp-scenarios) may contain references to other UA instance's address in the form `ua[0-9].host`.
- [Tests](#tests) may be templated using the [Template engine](#template engine).

---

## Test suite folder layout

**Sipplauncher** needs a test suite to run.
Test suite location is passed to Sipplauncher with `--testsuite` command-line option.
In case if this option is omitted, Sipplauncher uses a test suite, which is located at `<current_working_directory>/tmp-testsuite`.

To understand the layout required by Sipplauncher, we advise looking at the layout of the embedded mock test suite `sipplauncher/tmp-testsuite`.
The embedded mock test suite is present for the following purposes:

 - demonstrate **Sipplauncher** test suite layout and features
 - test if **Sipplauncher** works in your environment
 - ease development and testing of **Sipplauncher**

Here is the layout of the embedded mock test suite:

```bash
sipplauncher/tmp-testsuite/
├── normal-0000
│   ├── before.sh
│   ├── uac_ua2.xml
│   ├── uas_ua0.xml
│   └── uas_ua1.xml
├── normal-0001
│   ├── after.sh
│   ├── before.sh
│   ├── uac_ua1.xml
│   └── uas_ua0.xml
├── options-0000
│   └── uac_ua0.xml
├── options-0001
│   ├── uac_ua0.xml
│   ├── uac_ua1.xml
│   └── uac_ua2.xml
├── TEMPLATES
│   └── options.jinja2
└── users.csv
```

Therefore, a test suite should contain:

### Tests

A test's name is a subfolder name: `normal-0000`, `normal-0001`, etc.

> **_NOTE:_** Sipplauncher supports a special test for performing global configuration/checks. Default reserved name for this test is `GLOBAL` but it can be customised via [`--global-test-folder`](#optional-arguments) command-line argument. This test is not allowed to have any SIPp logic but can contain `before.sh`/`after.sh` [scripts](#scripts). Global `before.sh` will run once before the very first test and global `after.sh` will run once after the last test.

Each test folder contains all the information needed for a test to run:

#### SIPp scenarios

These are files named `uac_ua2.xml`, `uas_ua0.xml`, etc.

A scenario file name defines a launch order and role of a SIPp instance.
A scenario file name should match one of the regex patterns:

* `^(ua[cs])_(ua[0-9]+).xml$`.
* `^([a-zA-Z0-9]+)_(ua[cs])_(ua[0-9]+).xml$`

A scenario file name contains several parts:

1. `^([a-zA-Z0-9]+)` optional part.

      This part defines an ID of a **run group**, in which the scenario will be run.

      This part divides all the scenarios into groups and determines the order of running these groups.
      Here are the rules:

      * Scenarios from the same run group are run concurrently.
      * Different run groups are run consecutively, ordered by the run group ID value.

      If this part is absent, it's assumed that the scenario's run group ID is "" (empty string).

      For example:

          normal-0000
          ├── uac_ua0.xml
          └── uas_ua1.xml

      Here, it's assumed that all scenarios belong to the same run group ID "".
      And therefore, all these scenarios are run concurrently.

      Here is the example of a more complex [Test](#tests) folder layout:

          normal-0001
          ├── part0_uac_ua0.xml
          ├── part0_uas_ua1.xml
          └── part1_uac_ua0.xml

      Here, Sipplauncher will determine 2 run groups:

      * `part0`
      * `part1`

      Then, Sipplauncher will run concurrently `part0_uac_ua0.xml` and `part0_uas_ua1.xml` and wait for them to finish.

      If any of these scenarios fail, test execution stops.
      Otherwise, Sipplauncher then runs `part1_uac_ua0.xml`.

      `ua0` preserves the same [dynamically assigned](#dynamic-ip-address-assignment) IP address when running both run groups.

2. `(ua[cs])` mandatory part.

      This part defines the order of launching SIPp instances inside a **run group**.
      `uas` scenarios are launched before `uac` scenarios.

3. `ua[0-9]` mandatory part.

      This part defines an `instance name` inside a SIPp instance group.

      A SIPp instance in a group can refer to other SIPp instances in the same group using `ua[0-9].host` keywords in its scenario file.

      For example, we have files named `uac_ua2.xml` and `uas_ua0.xml` in a test folder.
      `uac_ua2.xml` may refer to SIPp instance, which runs`uas_ua0.xml`, using `ua0.host` keyword.

      This is possible due to the [Dynamic IP address assignment](#dynamic-ip-address-assignment) and [Keyword replacement](#keyword-replacement).
      First, dynamic IP addresses are allocated and assigned.
      Then, the [Template engine](#template-engine) replaces `ua[0-9].host` keywords with real IP addresses of SIPp instances.

      There shouldn't be duplicates of the SIPp `instance name` in the same **run group**.
      Here are the examples:

      Duplicate SIPp instance names are **disallowed** within the same default **run group**:

          normal-0000
          ├── uac_ua0.xml
          └── uas_ua0.xml

      Duplicate SIPp instance names are **disallowed** within the same **run group** `part0`:

          normal-0001
          ├── part0_uac_ua0.xml
          └── part0_uas_ua0.xml

      Duplicate SIPp instance names are **allowed** within different **run groups** `part0` and `part1`:

          normal-0002
          ├── part0_uac_ua0.xml
          └── part1_uas_ua0.xml

      SIPp instance preserves the same [dynamically assigned](#dynamic-ip-address-assignment) IP address when running both run groups.
      Therefore, in the above example, `ua0` will preserve its IP when running in group `part0` and `part1`.

#### Scripts

Files, which have `.sh` extension, are considered the scripts.

There are 2 predefined script names, which are automatically run by **Sipplauncher** if present:

1. `before.sh` is run before running the SIPp instance group.
2. `after.sh` is run after running the SIPp instance group.

These scripts could be used to provision a DUT with some configuration, which is needed for a test to pass.

All other scripts aren't run automatically by **Sipplauncher** but could be run from elsewhere.
For example, from the [SIPp scenario](#sipp-scenarios).

When preparing a test to run, the keywords inside all test's scripts are [replaced](#keyword-replacement).

If `before.sh` exits with non-zero exit code, a test execution stops.
If either `before.sh` or `after.sh` exits with non-zero exit code, the test is considered failed.

> **_NOTE:_** Special purpose global `before.sh`/`after.sh` scripts are [supported](#tests).

#### DNS zone description file

A file named `dns.txt` is considered the DNS zone description file.

When preparing a test to run, the keywords inside this file are [replaced](#keyword-replacement).

Then the contents of this file are added to the [Embedded DNS server](#embedded-dns-server).

After the test is finished, the file is removed from the [Embedded DNS server](#embedded-dns-server).

The example of a `dns.txt` contents:

```bash
ep1.example.com  A       {{ '{{' }}ua1.host{{ '}}' }}

# UDP SRV records
_sip._udp.example.com.         SRV [10, 60, 5060, "ep1.example.com."]

# TCP SRV records
_sip._tcp.example.com.         SRV [10, 60, 5060, "ep1.example.com."]

# TLS SRV records
_sip._tls.example.com.         SRV [10, 60, 5061, "ep1.example.com."]

# SIPS SRV records
_sips._tcp.example.com.         SRV [10, 60, 5061, "ep1.example.com."]
```

#### 3PCC Extended configuration file

A file named `3pcc.txt`, will be interpreted to adjust the SIPp call parameters. This file provides support for
the functionality [3PCC Extended](http://sipp.sourceforge.net/doc/reference.html#3PCC+Extended') defined in SIPp.

When preparing a test to run, the keywords inside this file are [replaced](#keyword-replacement). Each entry in the file
might match one identifier, one IP address, and a random port for a given UA.

An example of a `3pcc.txt` contents:

```bash
m;{{ ua0.host }}:8880
ua1;{{ ua1.host }}:8881

```


### Injection file

Injection file is passed to Sipplauncher with `--sipp-info-file` command-line option.
Sippluncher, in turn, passes this file to SIPp with `-inf` option.
SIPp reads a line from this file per each new call and replaces keywords in a scenario.

In case if this option is omitted, Sipplauncher uses pre-defined location `<testsuite_folder>/users.csv`.
If there is no file at this location, an injection file isn't used.

In the [embedded mock test suite](#test-suite-folder-layout), the injection file is `sipplauncher/tmp-testsuite/users.csv`.

### Templates

A template folder contains templates, which could be re-used by [Tests](#tests) to avoid code duplication.
A good design pattern is to extract an often-used code of a test into a template and then re-use that template.
Template expansion is performed by the [Template engine](#template engine).

A template folder is passed to Sipplauncher with `--template-folder` command-line option.
In case if this option is omitted, Sipplauncher uses pre-defined location `<testsuite_folder>/TEMPLATES`.
If there is no folder at this location, templates aren't used.

In the [embedded mock test suite](#test-suite-folder-layout), the template folder is `sipplauncher/tmp-testsuite/TEMPLATES`.

---

## Command-line arguments

Run this to see all available arguments:
```bash
sipplauncher -h
```

### Mandatory arguments

|argument name|argument value|description|
| --- | --- | --- |
|--dut|DUT|Device under test IP address|
|--testsuite|TESTSUITE|Path to a [Test suite](#test-suite-folder-layout).<br>Default: `<current_working_directory>/tmp-testsuite`.|

### Optional arguments
|argument name|argument value|description|
| --- | --- | --- |
|-h, --help||Show help message and exit|
|--template-folder|TEMPLATE_FOLDER|Path to a folder with [templates](#templates).<br>Default: `<testsuite>/TEMPLATES`.|
|--pattern-exclude|PATTERN_EXCLUDE|Regular expression to exclude tests.<br>If used with `--pattern-only` arg, and a test name matches both, the test is excluded.<br><br>Example: `--pattern-exclude options --pattern-exclude '.*_dns' --pattern-exclude '.*_tls'`.|
|--pattern-only|PATTERN_ONLY|Regular expression to specify the only tests which should be run.<br>If used with `--pattern-exclude` arg, and a test name matches both, the test is excluded.<br><br>Example: `--pattern-only options --pattern-only '.*_dns' --pattern-only '.*_tls'`.|
|--network-mask|NETWORK_MASK|Network mask, which is used for [Dynamic IP address assignment](#dynamic-ip-address-assignment).<br>Default: `24`.|
|--group|GROUP|Number of SIPp tests to be run at the same time.<br>Default: `1`.<br>Please see the [example](#run-all-tests-with-concurrent-grouping-by-3-tests).|
|--group-pause|GROUP_PAUSE|Pause between group executions.<br>Default: `0.8`.|
|--group-stop-first-fail||Stops after any test of the group fails.|
|--random||Selects randomly tests from the test pool (instead of alphabetical consecutive ordering).|
|--loop||Repeat tests in an endless loop (until interrupted by CTRL+C).<br>It could be used together with `group-stop-first-fail` arg in order to repeat some test endlessly until it fails, to reproduce some rare issue.|
|--dry-run||Dry run, simulates an execution without actual [SIPp scenarios](#sipp-scenarios) launch.|
|--fail-expected||OK if the execution fails.|
|--leave-temp||Don't remove [test run folder](#test-run-folder) after the test has finished.<br>By default, a [test run folder](#test-run-folder) is removed after the test has finished.|
|--keyword-replacement-values|KEYWORD_REPLACEMENT_VALUES|Custom [keyword values](#keyword-replacement) in JSON object format to be used by the [Template engine](#template-engine) to replace values in [Templated files](#templated-files).<br><br>Example: `--keyword-replacement-values '{ "ua1_username": "test1", "ua2_username": "test2", "some_url": "http://10.22.22.24:8080" }'`.|
|--no-pcap||Disable [capturing to pcap](#pcap-capturing) files.|
|--tls-ca-root-cert|TLS_CA_ROOT_CERT|[TLS CA root certificate](#tls) file (.pem format).<br>It must be used together with `tls-ca-root-key` arg.|
|--tls-ca-root-key|TLS_CA_ROOT_KEY|[TLS CA root key](#tls) file (.pem format).<br>It must be used together with `tls-ca-root-key` arg.|
|--sipp-transport|One of: u1, un, ui, t1, tn, l1, ln|SIPp -t param.<br>The default is `l1`, if [TLS](#tls) usage is auto-detected. Otherwise, it's `u1`.<br>[TLS](#tls) usage is auto-detected if any tls-related option is used.|
|--sipp-info-file|SIPP_INFO_FILE|SIPp `-inf` argument.<br>Used to specify an [Injection file](#injection-file).|
|--sipp-call-rate|SIPP_CALL_RATE|Calls per seconds, SIPp -r param. Be aware, that `--sipp-concurrent-calls-limit` could be hit before call rate.|
|--sipp-max-calls|SIPP_MAX_CALLS|Amount of calls to perform. SIPp `-m` argument.|
|--sipp-recv-timeout|SIPP_RECV_TIMEOUT|SIPp `-recv_timeout` argument.|
|--sipp-tls-version|One of:  1.0, 1.1, 1.2|SIPp `-tls_version` argument.<br>Please see [TLS](#tls).|
|--sipp-concurrent-calls-limit|Number|Maximum number of simultaneous calls. Default: 1. SIPp `-l` param. |
|--default_behaviors|DEFAULT_BEHAVIORS|SIPp `-default_behaviors` argument.|
|--global-test-folder|GLOBAL_TEST_FOLDER|Path to the folder which contains global provisioning or checking scripts.<br>Default: `GLOBAL`.|

---

## Common usage examples

### Run all tests consecutively

```bash
sipplauncher --dut 10.22.22.24 --testsuite <path_to_testsuite>
```

### Run all tests with concurrent grouping by 3 tests

Split all tests into concurrent groups of 3 tests in each group.
Next, run all groups consecutively.
3 tests inside a group are run concurrently.

```bash
sipplauncher --dut 10.22.22.24 --testsuite <path_to_testsuite> --group 3
```

### Run a single test

Let's assume, test suite contains a test named `normal-0000`.
To run only this test:


```bash
sipplauncher --dut 10.22.22.24 --testsuite <path_to_testsuite> --pattern-only normal-0000
```

### Run a single test concurrently (SIPp concurrency)

Let's assume, test suite contains a test named `normal-0000`.
To run this test concurrently in the scope of a single sipplauncher test run (utilising SIPp's capability to generate multiple calls from a single test definition):


```bash
sipplauncher --dut 10.22.22.24 --testsuite <path_to_testsuite> --pattern-only normal-0000 --sipp-max-calls 3 --sipp-call-rate 3 --sipp-concurrent-calls-limit 3
```

### Run a single test concurrently (sipplauncher concurrency)

Let's assume, test suite contains a test named `normal-0000`.
To run this test concurrently as number of unique sipplauncher test runs:


```bash
sipplauncher --dut 10.22.22.24 --testsuite <path_to_testsuite> --pattern-only normal-0000 --group 3 --total 3
```

---

## Test run folder

Before executing a test, Sipplauncher copies its content to a temporary test folder.
Default location of test run folder is `/var/tmp/sipplauncher/<test_name>/<test_run_id>`.
`test_name` matches test folder name from [Test suite folder layout](#test-suite-folder-layout).
`test_run_id` is assigned dynamically for each test run and is seen in [test result output](index.md#getting-started).

Then Sipplauncher [replaces keywords](#keyword-replacement) in the [Templated files](#templated-files).

Then Sipplauncher launches SIPp instances in the working directory of a [Test run folder](#test-run-folder).

After the test has finished, [Test run folder](#test-run-folder) contains:

- [scripts](#scripts) and [SIPp scenarios](#sipp-scenarios), which were run during the test
- [DNS zone description file](#dns-zone-description-file), which was served by the [Embedded DNS server](#embedded-dns-server)
- all [log files](#log-files)
- generated [TLS](#tls) certificates, private keys and [session keys](#decrypting-tls-traffic)
- [pcap](#pcap-capturing) file

By default, the [Test run folder](#test-run-folder) is deleted after the test has finished.
To change this behavior, please use `--leave-temp` command-line argument.

---

## Template engine

Sipplauncher uses [Jinja2](https://en.wikipedia.org/wiki/Jinja_(template_engine)) as a template engine.
Therefore, you can use Jinja2 syntax when defining the [Templated files](#templated-files).

A good example of the approach can be found in the [embedded mock test suite](#test-suite-folder-layout).

Templates could be placed either into a [Test](#tests) folder or in the [Templates](#templates) folder.
Both these locations are searched when Jinja2 imports a template into a test.

### Templated files

The [Template engine](#template-engine) processes the following files:

- [scripts](#scripts)
- [SIPp scenarios](#sipp-scenarios)
- [DNS zone description file](#dns-zone-description-file)

### Keyword replacement

The [Template engine](#template-engine) is also responsible for replacing keywords in the [Templated files](#templated-files).

Keywords could be either internal or supplied using `--keyword-replacement-values` command-line argument.

To define a keyword in a [script](#scripts) or [SIPp scenario](#sipp-scenarios), you should use `{{ '{{' }}keyword{{ '}}' }}` syntax.

#### Internal keywords

|keyword|desription|
|---|---|
|dut.host|the value, passed via `--dut` command-line argument.|
|test.name|the [Test](#tests) subfolder name.|
|test.run_id|the [Test](#tests) random run ID (size 6).|
|test.run_id_number|another random id (size 12) composed only of integers/digits.|
|ua[0-9].host|[Dynamically assigned IP address](#dynamic-ip-address-assignment) for the [test's](#tests) SIPp instance `ua[0-9]`.|

## Dynamic IP address assignment

Sipplauncher assigns random IP addresses from a DUT IP network before running each test.

Sipplauncher takes a DUT IP address, which is supplied via `--dut` command-line argument.
Then it applies a network mask, which is supplied via `--network-mask` command-line argument, to the DUT IP address.
The result is considered the DUT network.

Then Sipplauncher randomly allocates IP addresses from the DUT network.
The allocated address is then checked to be not yet assigned to another machine in the same LAN.
Then the address is assigned to a machine, which runs Sipplauncher.

The number of assigned IP addresses corresponds to the number of [SIPp scenarios](#sipp-scenarios) in a [test](#tests).

After the test has finished, the allocated IP addresses are deleted.

## Embedded DNS server

Sipplauncher has the DNS server inside.

This makes possible to mock DNS names resolution for a DUT.
Thus, if requested, Sipplauncher adds [dynamically](#dynamic-ip-address-assignment) assigned IP addresses to the embedded DNS server.
And then [SIPp scenarios](#sipp-scenarios) might use domain names instead of IP addresses.
This allows testing how a DUT works with regards to the DNS name resolution.

![](assets/images/sipplauncher_dns.png)

Of course, the DUT should be configured to use Sipplauncher's DNS service instead of regular DNS servers.
Usually, this requires patching the DUT's `/etc/resolve.conf` like this:

```bash
search example.com
nameserver 10.22.22.22
```

Here `10.22.22.22` - is the IP address of Sipplauncher's VM.

Sipplauncher launches the DNS service on UDP port `53`, if at least one [Test](#tests) has [DNS zone description file](#dns-zone-description-file) in it.

* When a [Test](#tests) is [prepared](developer_guide.md#1-pre-run), a [DNS zone description file](#dns-zone-description-file) is added to the DNS server.
* When a [Test](#tests) is [cleaned](developer_guide.md#3-post-run), a [DNS zone description file](#dns-zone-description-file) is removed from the DNS server.

The DNS server has only a single instance.
It's shared among all the [Tests](#tests).
Therefore, to support concurrent test execution (see `--group` command-line argument), tests should avoid defining overlapping DNS zone information.

For example, `TestA` defines such entry in its `dns.txt`:

```
ep1.example.com  A       {{ '{{' }}ua1.host{{ '}}' }}
```

And `TestB` defines the same entry in its `dns.txt`:

```
ep1.example.com  A       {{ '{{' }}ua2.host{{ '}}' }}
```

Then a single DNS server instance will be configured this way:

```
ep1.example.com  A       10.22.22.123
ep1.example.com  A       10.22.22.210
```

Therefore, information for `ep1.example.com` is overlapping.
This will cause undefined behavior when a DUT attempts to resolve `ep1.example.com`.

!!! Note
    The same issue will occur if `TestB` defines an entry in its `dns.txt` this way:

    ```
    ep1.example.com  A       {{ '{{' }}ua1.host{{ '}}' }}
    ```

    Due to the [Dynamic IP address assignment](#dynamic-ip-address-assignment), `{{ '{{' }}ua1.host{{ '}}' }}` will be replaced with different IP addresses for TestA and TestB.
    And thus the collision will occur.

## TLS

Sipplauncher supports SIP TLS endpoints.
For TLS to work on a UAS SIP endpoint, SSL certificate and private key should be provided to a UAS instance.
Sipplauncher by default generates ephemeral SSL certificate and private key for each UAS.
And launches UAS using this SSL certificate and private key.

However, in this case, security issues regarding using certificates, issued by not-trusted CA, are likely to arise on a DUT UAC side,
when the DUT as UAC tries to connect to such a UAS.

To overcome this issue, `--tls-ca-root-cert` and `--tls-ca-root-key` Sipplauncher arguments could be handy.
If these arguments were provided, Sipplauncher signs a generated SSL certificate and private key with supplied CA root certificate and private key.
A DUT should be configured to trust this CA.
Then a connection is established without security issues.

The generated SSL certificates and private keys are saved to a [Test run folder](#test-run-folder).

TLS packet exchange is stored in a .pcap file and could be [decrypted](#decrypting-tls-traffic).

## Pcap capturing

By default, Sipplauncher captures all packets, which have [dynamically assigned IP addresses](#dynamic-ip-address-assignment) as either `src` or `dst`.
Packet exchange is captured into a .pcap file, which could be opened with the Wireshark application.
Pcap file is named `sipp-<test_run_id>.pcap` and is stored in a [Test run folder](#test-run_folder).

You can disable [Pcap capturing](#pcap-capturing) with `--no-pcap` command-line argument.

### Decrypting TLS traffic

Usually, it's easy to decrypt SSL packet exchange, if you have SSL private key.
However, this is not the case for the [Diffie-Hellman](https://en.wikipedia.org/wiki/Diffie%E2%80%93Hellman_key_exchange) encryption algorithm.
This algorithm uses per-session dynamic keys.

Sipplauncher helps to decrypt even Diffie-Hellman-encoded packet exchange.
For this, Sipplauncher logs per-session dynamic keys into `tls_premaster_keys.txt` file in a [Test run folder](#test-run-folder).
Then this file could be used to decrypt the packet exchange in Wireshark.

You can go to `Edit` → `Preferences` → `Protocols` → `SSL` and choose `tls_premaster_keys.txt` in `(Pre)-Master-Secret log filename` field:

Wireshark SSL preferences ![](assets/images/wireshark_tls_premaster_keys.png)

To enable this feature, you should [install Sipplauncher from the source](index.md#install-sipplauncher).

---

## Log files

Logging facility is controlled via `/usr/local/etc/sipplauncher/sipplauncher.configlog.conf`.

By default, Sipplauncher logs to following files:

* `/tmp/sipplauncher.log` - general log file.
* `/var/tmp/sipplauncher/<test_name>/<test_run_id>/sipplauncher.log` - log, that contains information regarding execution of test `test_name`.
* `/var/tmp/sipplauncher/<test_name>/<test_run_id>/pysipp.launch.log` - log, that contains information regarding running SIPp instances of test `test_name`.
* `/var/tmp/sipplauncher/<test_name>/<test_run_id>/tls_premaster_keys.txt` - log of captured [TLS Pre-master keys](#decrypting-tls-traffic).
* `/var/tmp/sipplauncher/<test_name>/<test_run_id>/ua[0-9]..` - varios [SIPp scenario](#sipp-scenario) `ua[0-9]` logs, which were produced by SIPp.


## 3PCC Extended

Sipplauncher provides support for SIPp's [3PCC Extended](http://sipp.sourceforge.net/doc/reference.html#3PCC+Extended'),
where different instances can communicate independently not sending/receiving SIP messages.
This is helpful when **you want to synchronize two (or more) scenarios**, or in fact, you just want to emulate a 3PCC controller.

This functionality is based on a configuration file [3pcc.txt](#3PCC Extended configuration file). Please check the details of that file in that section.

Then you might configure the master and slaves instances. There must be just one master instance and one or multiple slaves.
Master instance will be identified as **m** and is the one sending the first `<sendCmd>`. It's the last one to be started so it will connect to the remote slaves.
Slaves can have any identifier.

Notice that SIPp will check the scenarios at runtime, and may fail if the master instance doesn't have a `<sendCmd>` tag or slaves don't have a `<recvCmd>`.
If one of your UA scenarios doesn't have any of these tags, just don't add it to [3pcc.txt](#3PCC Extended configuration file) file.


Then in your scenarios you will be able to use SIPp `<sendCmd>` and `<recvCmd>`.

```bash
<sendCmd dest="ua01">
  <![CDATA[
    Call-ID: [call_id]
    From: m
  ]]>
</sendCmd>
```

Note that on `<sendCmd>` it's mandatory to add a `From:` header with the id of the sender and also set the **dest** attribute to set the destination
of the UA you want to send the message.

On the other side we have `<recvCmd>`:

```bash
<recvCmd src="m">
  <action>
     <ereg regexp="Content-Type:.*"
           search_in="msg"
           assign_to="dummy"/>
  </action>
</recvCmd>

<Reference variables="dummy" />
```

Here we can specify optionally the source of the message in order to validate it. Additionally, we can extract values from
the message using `<ereg>` actions.

