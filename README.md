
# SIH Entity Mapping

This project consists of three main components: `poppler`, `ocr`, and `llm`, working together to process PDF files using image conversion, optical character recognition (OCR), and large language models (LLM) for entity extraction.

## 🚀 **Steps to Run**

Follow these steps to run the servers:

1. **Navigate to the Root Directory:**

   ```bash
   cd /path/to/project
   ```
2. **Start the Poppler Server:**

   ```bash
   python -m poppler.main
   ```

   * This serves as a PDF-to-Image converter and includes an in-built API server.
3. **Start the OCR Server:**

   ```bash
   python -m ocr.main
   ```
4. **Start the LLM Server:**

   ```bash
   python -m llm.main
   ```

✅ All three servers will begin communicating seamlessly if they are running on the **same system.**

---

## 🌐 **Running on Multiple Systems**

For better performance or if you choose to run the components on different devices, follow these steps:

1. Ensure all devices are connected to the **same fast network.**
2. On each device where the `ocr` and `llm` servers are running, find the network IP address using the following command:
   ```bash
   ipconfig
   ```
3. Update the `.env` file in the root directory with the IP addresses of the respective servers:
   ```env
   OCR_SERVER=<OCR_IP>
   LLM_SERVER=<LLM_IP>
   ```
4. Repeat the previous **Steps to Run** for each server on its designated device.

---

## ⚡ **Additional Tips**

* Ensure `Python` is installed and available in your environment.
* Install required dependencies using:
  ```bash
  pip install -r requirements.txt
  ```
* Confirm that the firewall or antivirus is not blocking communication between the servers.

---

For any issues or troubleshooting, refer to the respective logs of each service or contact the development team.
