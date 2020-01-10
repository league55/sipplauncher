![Logo](assets/images/logo.png)

**Sipplauncher** - automate your VoIP testing

---

## Overview

**Sipplauncher** is a Python-3 application.

Features:

- Execute your [SIPp](http://sipp.sourceforge.net) test suite with just **one command** in one VM/container.
- Easily add SIP traffic testing to your **continuous integration pipeline**.
- Run **multiple SIPp scenarios** at the same time. Highly-configurable.
- [Dynamically](user_guide/#dynamic-ip-address-assignment) creates networking pseudo-interfaces, to which SIPp instances will be bound.
- Each test execution will generate a [.pcap file](user_guide/#pcap-capturing) if desired.
- Ability to provision and/or clean-up Device Under Test (DUT) using [BASH scripts](user_guide/#scripts).

![](assets/images/sipplauncher.png)

Supported transports:

- UDP
- TCP
- [TLS](user_guide/#tls). You can either supply your certificate, or **Sipplauncher** could generate an intermittent one for you.

---

## Requirements

### Supported operating systems

- CentOS-7
- Ubuntu-18.04.3

Other Linux-based distros might suffice as well.
However, **Sipplauncher** is developed and tested only on the above platforms.
Therefore, some extra effort might be required to make **Sipplauncher** work properly on other platforms.

### Supported network architecture

- **Sipplauncher** and DUT should be located within the same physical (or emulated) Ethernet network.
- **Sipplauncher** and DUT IP addresses should be located within the same logical IP network
- **Sipplauncher** and DUT should have no firewalls between them
- IPv4 only. IPv6 is not supported

!!! Note

    **Sipplauncher** [dynamically assigns](user_guide/#dynamic-ip-address-assignment) random IP addresses to a host, on which it's launched.
    The checks are done, to not accidentally use an IP address, which is already assigned to some other machine in the same LAN.
    However, to avoid impact on your LAN, it's recommended to run **Sipplauncher** in a private LAN or an emulated environment.

---

## Installation

Below instructions will guide you on how to perform installation and self-test.

### Install prerequisites

This part is dependant on the selected platform:

For CentOS-7:

```bash
yum install -y wget git make which tcpdump openssl-devel gcc python3-pip
wget http://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
rpm -ivh epel-release-latest-7.noarch.rpm
yum install -y sipp
```

For Ubuntu-18.04.3:

```bash
apt-get update -qy
apt-get install -y git sip-tester tcpdump libssl-dev gcc python3-pip
```

### Install **Sipplauncher**
This part is common for all platforms:

```bash
git clone https://github.com/zaleos/sipplauncher.git -b develop
cd sipplauncher
make install-reqs
make install-all
```

### Perform self-testing

```bash
make install-reqs-test
make test
```

All tests should pass without error.

---

## Getting started

Now let's try running the [embedded mock test suite](user_guide/#test-suite-folder-layout).
Let's assume that DUT's IP address is `10.22.22.24`.

Go to **Sipplauncher** directory and run:

```bash
sipplauncher --dut 10.22.22.24 --testsuite tmp-testsuite
```

You should see similar output:

![](assets/images/sipplauncher.gif)

This means, test suite run has succeded.
Individual tests have failed, but this is expected, because these are mock tests, not tied to your DUT.

To have a real working test suite for your DUT, you should write it.
You can take the [embedded mock test suite](user_guide/#test-suite-folder-layout) as an example.

To proceed, please see [User Guide](user_guide).
