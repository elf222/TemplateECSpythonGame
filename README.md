## Setup

### macOS/Linux

python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

### Windows

py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt

## Run

python main.py

## Web build

python -m pygbag .
