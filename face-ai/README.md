<p align="center"><img width="20%" src="app/data/images/favicon.png" /></p>

# 👩 Face AI
We will use Face Detection, Face Recognition and some other related offline AI technologies to build our open-source, cross-platform app. This will provide security without the need of an active Internet connection.

> Overview: The app uses KivyMD and Kivy mainly for the UI. The app uses `NumPy`, `OpenCV` & `OnnxRuntime` as the logic backbone.

### 🤔 Why would you choose our app? (Features)
👉 Offline Face Detection and Recognition. <br>
👉 Store secret files which can only be unlocked by your face. On `non-android` platform, files will be encrypted. <br>
👉 Cross-platform and Open Source. <br>

## 💰 Sponsor Me
You can buy me a coffee via [this link](https://www.paypal.com/paypalme/soomnathsdas) or tap on below image. Thank you 🙏. <br>
<a href="https://www.paypal.com/paypalme/soomnathsdas"><img src="./docs/images/donate.svg" height="40"></a>

## 📽️ Demo
You can click on the below Image or this [Youtube Link](https://www.youtube.com/watch?v=GezJh-6yIKg) to see the demo. Please let me know in the comments, how do you feel about this App. <br>
[![FaceAiThumb](./docs/images/gitThumb.jpg)](https://www.youtube.com/watch?v=GezJh-6yIKg)

## 🖧 Our Scematic Architecture
<p align="left"><img width="80%" src="docs/images/FaceRecognitionFlow.gif" /></p>

| Model | Source Link | Size  | Remarks |
| :---- | :---------- | :---: | ------- |
| det_10g.onnx | [buffalo_l](https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip) | 17MB | Face Detection |
| arc.onnx | [arcface-onnx](https://huggingface.co/garavv/arcface-onnx/tree/main) | 137MB | Face Recognition |


## 🧑‍💻 Quickstart Guide

### 📱 Download & Run the Android App
You can check the [Releases](https://github.com/daslearning-org/face-ai/releases) and downlaod the latest version of the android app on your phone.

> If you use the `Download` button from the app, you can save the images in one of the mentioned folders: `Downloads`, `Pictures` and videos in `Downloads`, `Movies`, `Videos` due android file access restrictions on `Android 11+`.

### 💻 Download & Run the Windows or Linux App
You can check the [Releases](https://github.com/daslearning-org/face-ai/releases) and downlaod the latest version of the app on your `Linux` or `Windows` platform. The Linux app has no extension, you may need to change the permission of the file to run it. The Windows app will have an `exe` extension, just double click & run it (You may need to create an exception for Antivirus if there is any detection).

### 🐍 Run with Python

1. Clone the repo
```bash
git clone https://github.com/daslearning-org/face-ai.git
```

2. Run the application
```bash
cd face-ai/app
pip install -r requirements.txt # virtual environment is recommended
python main.py
```

## 🦾 Build your own App
The Kivy project has a great tool named [Buildozer](https://buildozer.readthedocs.io/en/latest/) which can make mobile apps for `Android` & `iOS`

### 📱 Build Android App
A Linux environment is recommended for the app development. If you are on Windows, you may use `WSL` or any `Virtual Machine`.

```bash
# add the python repository
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update

# install all dependencies.
sudo apt install -y ant autoconf automake ccache cmake g++ gcc lbzip2 libffi-dev libltdl-dev libtool libssl-dev make openjdk-17-jdk patch patchelf pkg-config unzip wget zip git python3.14 python3.14-venv python3.14-dev # python3-dev python3-pip (if required)

# optionally you may check the java installation with below commands
java -version
javac -version

# install python modules
git clone https://github.com/daslearning-org/face-ai.git
cd face-ai/app
python3.11 -m venv .env # create python virtual environment
source .env/bin/activate
pip install -r req_android.txt

# build the android apk
buildozer android debug # this may take a good amount of time for the first time & will generate the apk in the bin directory
```

### 🖳 Build Computer Application (Windows / Linux / MacOS)
A `Python` virtual environment is recommended and please follow the same steps from above till the pip module installations (do not require buildozer for desktop apps). It builds a native app depending on the OS type i.e. `.exe` if you are running `PyInstaller` from a Windows machine. Build computer apps from [docker image](https://hub.docker.com/r/cdrx/pyinstaller-windows) for any OS type.

```bash
# install pyinstaller
pip install pyinstaller

# generate the spec file <<OPTIONAL>>
pyinstaller --name "dlDesktop" --windowed --onefile main.py # optional as it is already created in the repo

# then update the spec file as needed
# then build your app which will be native to the OS i.e. Linux or Windows or MAC
pyinstaller dlDesktop.spec
```
