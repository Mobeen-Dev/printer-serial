source ~/.espressif/v6.0.3/esp-idf/export.sh

idf.py reconfigure
idf.py build

cd build

python -m esptool --chip esp32s3 -p /dev/ttyACM0 -b 460800 --before default-reset --after hard-reset --no-stub write-flash @flash_args

idf.py -p /dev/ttyACM0 monitor
idf.py -p /dev/ttyACM0 monitor
