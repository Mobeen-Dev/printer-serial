source ~/.espressif/v6.0.3/esp-idf/export.sh

idf.py -p /dev/ttyACM0 monitor

idf.py reconfigure


idf.py -p /dev/ttyACM0 monitor