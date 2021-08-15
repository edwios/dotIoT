# ESP32 README

This folder contains all works related to the ESP32 module.

Note
====
Some of these require large Flash and RAM.

### Individual READMEs
-----

mini_gateway.py

This is the code for a BLE Mesh to MQTT gateway. It accepts commands from MQTT and send those commands to the BLE mesh. Statuses and replies from the BLE mesh are published to MQTT.

### Configuration
Send the network configuration JSON file to the config topic to update the BLE mesh network and devices information.

### Commands and Operations
Commands and Operations are sent to the mini_gateway via MQTT topic 'command'. Commands take no parameters and Operations take zero or more parameters. Operations that have more than one parameters are separated into three parts in the form of:

`Device/Operation:Parameter 1[,parameter 2, parameter 3, ...]`

All parameters except CCT and Brightness are hexidecimal strings (without 0x).

E.g.

<pre>
`Hallyway lamp/on`
`Stairs light/dim:5`
`Coolwarm/cct:2700`
`Discoball/rgb:00FFE8`
`Desklamp/get_timer:15`
`Desklamp/set_time:2022,2,18,7,22,38`
</pre>

Parameter for `raw` takes the form of `AABBCCCCCC` where<br/>
&nbsp;&nbsp;&nbsp;&nbsp;`AA` is opcode<br/>
&nbsp;&nbsp;&nbsp;&nbsp;`BB` is expected callback opcode<br/>
&nbsp;&nbsp;&nbsp;&nbsp;`CCCCCC` are pars for opcode `AA`

E.g. 

`Bed lamp/raw:D0DC010100`

### Supported Commands

debug, nodebug, refresh

### Supported Operations with no parameters

on, off, power, get_geo, get_sunrise, get_sunset, 

### Supported Operations with 1+ parameters

dim, cct, rgb, get_dst, get_timer, get_scene, get_astro, get_time, get_power, get_status, get_countdown

set_time, set_dst, set_countdown, set_group, set_remote

del_group, del_scene

raw, at
