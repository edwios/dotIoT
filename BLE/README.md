# dotIoT - BLE Gateway
dotIoT project linking up Telldus Live! and Smartline Flow

This is an early trial linking up the Smartline Flow devices with the Telldus platform. The main objectives are:
1. Look into what is needed to facilitate this who setup,
2. Create a path for the dotIoT A.I. core to include Smartline Flow items under her control,
3. Solve an immediate headache in my home where the automation interfers with people dynamics.

There are a few python scripts deveveloped to bring upon this integration. For usage instructions, run script with option --help :

- httpserver.py
	This script aimed to provide a simple and unsecured HTTP server to receive commands sent from the events created in Telldus Live!. These commands then translated into appropriate MQTT messages and sent to the MQTT broker.

- lds.py
	This is a simple gateway constructed to listen to commands sent over MQTT and translate these commands into appropriate PDU of the Telink mesh, and send it out.
	It can also be used to scan the BLE mesh network for devices to connected to. At the moment, only Telink mesh is supported.

- leGateway.py
	This is a simple gateway constructed to gather some data from a BLE device and publish the data through MQTT to the MQTT broker.

