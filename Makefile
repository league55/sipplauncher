#
# Interface to Python project
#


PYTHON=`which python3`
export PVERSION := $(shell grep '^VERSION' sipplauncher/utils/Defaults.py | cut -d "=" -f 2 | sed "s,',,g" | sed -e 's/^[[:space:]]*//')

ifdef CIRCLE_BRANCH
	CURRENT_GIT_BRANCH_TMP := $(CIRCLE_BRANCH)
else
	CURRENT_GIT_BRANCH_TMP := $(shell if hash git  2>/dev/null; then git symbolic-ref --short -q HEAD; else echo 'unknown'; fi)
endif
CURRENT_GIT_BRANCH := $(subst  /,-,$(CURRENT_GIT_BRANCH_TMP))

help: list

clean:
	rm -fr build/ dist/ *.egg-info/ .cache/ {test_log,test_junit}.xml tmp.cython* *~ 2>&1 || true
	find  sipplauncher/ -type f -regex ".*\.\(c\|pyc\|pyo\|so\|.*~\)" -exec rm -fr '{}' +; 2>&1 || true
	find  sipplauncher/ -type d -empty -delete 2>&1 || true
	find  test/ -type f -regex ".*\.\(c\|pyc\|pyo\|so\|.*~\)" -exec rm -fr '{}' +; 2>&1 || true
	rm -fr libsslkeylog.so

clean-all: clean
	find . -type f -regex ".*\.\(.*~\)" -exec rm -fr '{}' +; 2>&1 || true
	find . -type d -name '__pycache__' -exec rm -fr '{}' +; 2>&1 || true
	rm -fr /home/vagrant/tmp-env-zaleos-sipplauncher/local/etc/sipplauncher/ 2>&1 || true

develop:
	$(PYTHON) setup.py develop

lint:
	# flake8 --ignore F811,F401,E402,E501,E731 sipplauncher test
	# flake8 --ignore F401,E501 test
	flake8 --ignore E402,E731 --max-line-length=99 sipplauncher

fix-autopep8:
	find sipplauncher/ -name '*.py' -exec autopep8 --in-place --max-line-length 80 '{}' \;

test:
# --capture=sys to catch app stdout/stderr printouts to in-mem files instead of spoiling our test execution output
	$(PYTHON) -m pytest -v -s test/test_*.py -rx -l --durations=10 --basetemp=/tmp --capture=sys

install-reqs-sipplauncher:
	echo '' ;
	echo '* Installing requirements: sipplauncher'
	$(PYTHON) -m pip install -r requirements.txt --upgrade || exit 1 ;

install-reqs-test:
	echo '' ;
	echo '* Installing requirements: test' ;
	$(PYTHON) -m pip install -r requirements_test.txt --upgrade --no-cache-dir || exit 2 ;

install-reqs-build:
	echo '' ;
	echo '* Installing requirements: build' ;
	$(PYTHON) -m pip install -r requirements_build.txt --upgrade || exit 3 ;

install-reqs-docs:
	echo '' ;
	echo '* Installing requirements: docs' ;
	$(PYTHON) -m pip install -r requirements_docs.txt --upgrade || exit 4 ;

install-reqs: install-reqs-sipplauncher install-reqs-test install-reqs-build install-reqs-docs

define f_python_install
@echo "Installing $1"
$(PYTHON) setup.py install --record installed_files_$1.txt
endef

define f_python_uninstall
@echo "Uninstalling $1"
$(PYTHON) setup.py develop --uninstall
cat installed_files_$1.txt | xargs rm -rf
rm -frv installed_files_$1.txt
endef

PYTHON_TARGETS := sipplauncher
PYTHON_TARGETS_INSTALL_OBJ := $(addprefix install-, $(PYTHON_TARGETS))
PYTHON_TARGETS_UNINSTALL_OBJ := $(addprefix uninstall-, $(PYTHON_TARGETS))

libsslkeylog.so: sslkeylog.c
	$(CC) sslkeylog.c -shared -o libsslkeylog.so -fPIC -ldl

$(PYTHON_TARGETS_INSTALL_OBJ): clean libsslkeylog.so
	$(call f_python_install,$(subst install-,,$@))

$(PYTHON_TARGETS_UNINSTALL_OBJ): clean
	$(call f_python_uninstall,$(subst uninstall-,,$@))

install-all: $(PYTHON_TARGETS_INSTALL_OBJ)
uninstall-all: $(PYTHON_TARGETS_UNINSTALL_OBJ)

check-env-git-branch:
ifneq ($(CURRENT_GIT_BRANCH),master)
	$(error Not in "master" branch. Detected branch: "$(CURRENT_GIT_BRANCH)"))
else
	@echo Detected branch: "$(CURRENT_GIT_BRANCH)"
endif

upload-pypi: check-env-git-branch
	echo '' ;
	echo '* Uploading using twine' ;
	$(PYTHON) -m pip install --user --upgrade setuptools wheel
	$(PYTHON) setup.py sdist bdist_wheel
	$(PYTHON) -m pip install --user --upgrade twine
	twine upload dist/*$(PVERSION)* ;

.PHONY: list test
list:
	@$(MAKE) -pRrq -f $(lastword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$' | xargs

version:
	@echo $(PVERSION)

serve-docs:
	mkdocs serve -a 0.0.0.0:8000

deploy-docs:
	mkdocs gh-deploy --clean
