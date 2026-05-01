# SIM900-InternetBrowser
Its a simple SIM900 internet browser written in python, to run it you need to connect a USB-UART converter to the SIM900 module. It uses AT commend to download HTML and convert it into text, if there are any images, it will download it and show it. It support only simple pages and it only runs pages without HTTPS requirment.
Dont forget to change your APN and COM port in code!
And delete the SIM card pin code if your card doesnt have it!
Instructions:
Run "pip install -r requirements.txt"
Then check your COM port.
Change COM port in code.
Power up the SIM900 board and wait for start of searching network
Run "sim900net.py"
Wait.
If the result of AT commend "AT+SAPBR=1,1" is ERROR in the console you need to restart the program (the sim900 does not immediatly connect to netwok)
After setup is done type in your site domain (for example "example.com" it should work) and click "POBIERZ"
And wait to the text to show up (if site contains images, you need to wait for the images to download)

AND ITS DONE!


