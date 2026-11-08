idf_component_register(
    SRCS
        "esp32_thermal_printer.cpp"
        "ThermalPrinter.cpp"
        "BitmapCanvas.cpp"
        "GraphGenerator.cpp"
    INCLUDE_DIRS
        "."
    REQUIRES
        esp_driver_uart
        esp_driver_gpio
        led_strip
        esp_timer
        freertos
        log
)

target_compile_options(${COMPONENT_LIB} PRIVATE -std=gnu++17)