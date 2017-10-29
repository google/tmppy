#!/bin/bash

set -e

: ${N_JOBS:=2}

if [ "$STL" != "" ]
then
  STLARG="-stdlib=$STL"
fi

case $OS in
linux)
    docker rm -f tmppy &>/dev/null || true
    docker run -d -it --name tmppy --privileged polettimarco/fruit-basesystem:ubuntu-$UBUNTU
    docker exec tmppy mkdir tmppy
    docker cp . tmppy:/tmppy
    
    docker exec tmppy bash -c "
        export COMPILER=$COMPILER; 
        export N_JOBS=$N_JOBS;
        export STLARG=$STLARG; 
        export OS=$OS;
        cd tmppy; extras/scripts/postsubmit-helper.sh $1"
    exit $?
    ;;

osx)
    export COMPILER
    export N_JOBS
    export STLARG
    export OS
    extras/scripts/postsubmit-helper.sh "$@"
    exit $?
    ;;

*)
    echo "Unsupported OS: $OS"
    exit 1
esac
