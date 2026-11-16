# Dashboard Analisis E-Commerce Olist 

Proyek akhir kelas **Belajar Analisis Data dengan Python** (Dicoding). Proyek ini menganalisis *Brazilian E-Commerce Public Dataset by Olist* periode Januari 2017–Agustus 2018 untuk menjawab dua pertanyaan bisnis:

1. Kategori produk apa yang menyumbang pendapatan tertinggi, dan bagaimana trennya?
2. Negara bagian mana yang paling sering mengalami keterlambatan pengiriman, dan bagaimana dampaknya pada skor ulasan?

Analisis lanjutan yang digunakan: **RFM analysis**, **geospatial analysis**, dan **clustering manual (binning)**.

## Struktur Proyek

```
submission
├── dashboard
│   ├── dashboard.py       # aplikasi Streamlit
│   ├── main_data.csv      # data bersih hasil notebook
│   └── geo_state.csv      # titik pusat koordinat per state
├── data                   # dataset mentah (8 file CSV)
├── notebook.ipynb         # proses analisis lengkap
├── README.md
├── requirements.txt
└── url.txt                # tautan dashboard di Streamlit Cloud
```

## Setup Environment - Anaconda

```
conda create --name main-ds python=3.11
conda activate main-ds
pip install -r requirements.txt
```

## Setup Environment - Shell/Terminal

```
mkdir proyek_analisis_data
cd proyek_analisis_data
pipenv install
pipenv shell
pip install -r requirements.txt
```

Atau dengan `venv` bawaan Python:

```
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
```

## Menjalankan Dashboard

Jalankan dari folder root proyek (folder yang berisi `README.md`):

```
streamlit run dashboard/dashboard.py
```

Dashboard akan terbuka di browser pada alamat `http://localhost:8501`.

## Menjalankan Notebook

- **Google Colab:** unggah `notebook.ipynb` ke Colab, lalu jalankan semua sel (*Runtime → Run all*). Jika folder `data/` belum ada, dataset otomatis diunduh dari Google Drive Dicoding.
- **Lokal (Jupyter):** buka `notebook.ipynb` dari folder root proyek, lalu jalankan semua sel. Dataset dibaca dari folder `data/`.

Sel terakhir notebook menghasilkan ulang `dashboard/main_data.csv` dan `dashboard/geo_state.csv`.
