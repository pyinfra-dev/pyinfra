#!/usr/bin/env bash

pyinfra @docker/ubuntu,@docker/centos fact os

pyinfra @docker/ubuntu,@docker/centos all-facts
