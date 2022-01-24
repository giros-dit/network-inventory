#!/bin/bash
SDIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYBINDPLUGIN=`/usr/bin/env python -c 'import pyangbind; import os; print ("{}/plugin".format(os.path.dirname(pyangbind.__file__)))'`
pyang --plugindir $PYBINDPLUGIN -f pybind -p $SDIR/yang/ -o $SDIR/catalog_connector/models/yang/yang_catalog.py $SDIR/yang/yang-catalog@2018-04-03.yang

if [[ $? -ne 0 ]]
then
	echo "Failed. Bindings could not be generated."
else
	echo "Bindings successfully generated!"
fi
