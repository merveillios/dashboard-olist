"""Dashboard E-Commerce Olist (Jan 2017 - Agu 2018)."""
import os

import folium
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st
from streamlit_folium import st_folium

st.set_page_config(page_title="Dashboard E-Commerce Olist", page_icon="📦", layout="wide")
sns.set_theme(style="whitegrid")

MAIN_COLOR = "#1F6F8B"
GREY = "#C8C8C8"
ALERT = "#D1495B"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Load data (di-cache agar tidak dibaca ulang setiap ada interaksi)
@st.cache_data
def load_data():
    df = pd.read_csv(os.path.join(BASE_DIR, "main_data.csv"), parse_dates=["order_purchase_timestamp"])
    geo = pd.read_csv(os.path.join(BASE_DIR, "geo_state.csv"))
    return df, geo


main_df, geo_state_df = load_data()


# Helper: setiap fungsi menerima data yang sudah difilter
def to_orders(df):
    """Satu baris per pesanan (main_data berisi satu baris per barang)."""
    return df.drop_duplicates("order_id")


def create_monthly_df(df):
    monthly = df.groupby(df["order_purchase_timestamp"].dt.to_period("M")).agg(
        jumlah_pesanan=("order_id", "nunique"), pendapatan=("price", "sum")
    )
    monthly.index = monthly.index.to_timestamp()
    return monthly


def create_category_df(df):
    cat = df.groupby("product_category").agg(
        pendapatan=("price", "sum"), jumlah_pesanan=("order_id", "nunique")
    ).sort_values("pendapatan", ascending=False)
    cat["porsi_%"] = cat["pendapatan"] / cat["pendapatan"].sum() * 100
    return cat


def create_state_df(orders):
    state = orders.groupby("customer_state").agg(
        jumlah_pesanan=("order_id", "count"),
        rata2_hari_kirim=("delivery_days", "mean"),
        persen_terlambat=("is_late", "mean"),
        rata2_skor=("review_score", "mean"),
        pendapatan=("payment_value", "sum"),
    )
    state["persen_terlambat"] *= 100
    return state


def create_rfm_df(orders):
    ref_date = orders["order_purchase_timestamp"].max() + pd.Timedelta(days=1)
    rfm = orders.groupby("customer_unique_id").agg(
        last_purchase=("order_purchase_timestamp", "max"),
        frequency=("order_id", "nunique"),
        monetary=("payment_value", "sum"),
    )
    rfm["recency"] = (ref_date - rfm["last_purchase"]).dt.days
    # Skor kuartil; rank() dipakai agar qcut tetap jalan walau ada nilai sama
    rfm["R"] = pd.qcut(rfm["recency"].rank(method="first"), 4, labels=[4, 3, 2, 1]).astype(int)
    rfm["M"] = pd.qcut(rfm["monetary"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
    rfm["F"] = rfm["frequency"].clip(upper=3)

    conditions = [
        (rfm["F"] >= 2) & (rfm["R"] >= 3),
        (rfm["F"] >= 2),
        (rfm["R"] >= 3) & (rfm["M"] == 4),
        (rfm["R"] >= 3),
        (rfm["M"] == 4),
    ]
    choices = ["Pelanggan Setia", "Setia tapi Mulai Pasif", "Pelanggan Bernilai Tinggi Baru", "Pelanggan Baru", "Pelanggan Bernilai Tinggi Tidur"]
    rfm["segment"] = np.select(conditions, choices, default="Pelanggan Tidur")
    return rfm


# Sidebar: filter periode
min_date = main_df["order_purchase_timestamp"].min().date()
max_date = main_df["order_purchase_timestamp"].max().date()

with st.sidebar:
    st.title("📦 Olist E-Commerce")
    st.caption("Analisis pesanan terkirim, Jan 2017–Agu 2018")
    date_range = st.date_input(
        "Rentang tanggal pembelian", value=[min_date, max_date], min_value=min_date, max_value=max_date
    )
    if len(date_range) != 2:
        st.info("Pilih tanggal awal dan akhir.")
        st.stop()
    start_date, end_date = date_range
    top_n = st.slider("Jumlah kategori ditampilkan", min_value=5, max_value=15, value=10)
    st.markdown("---")
    st.caption("Sumber: Brazilian E-Commerce Public Dataset by Olist (Kaggle)")

filtered = main_df[
    (main_df["order_purchase_timestamp"].dt.date >= start_date)
    & (main_df["order_purchase_timestamp"].dt.date <= end_date)
]
if filtered.empty:
    st.warning("Tidak ada data pada rentang tanggal ini.")
    st.stop()

orders = to_orders(filtered)
monthly_df = create_monthly_df(filtered)
category_df = create_category_df(filtered)
state_df = create_state_df(orders)
rfm_df = create_rfm_df(orders)

# Header & KPI
st.title("Dashboard Penjualan & Pengiriman Olist")
st.caption(f"Periode: {start_date:%d %b %Y} – {end_date:%d %b %Y}")

st.markdown(
    "<style>[data-testid='stMetricValue']{font-size:1.7rem;}</style>",
    unsafe_allow_html=True,
)

k1, k2, k3 = st.columns(3)
k1.metric("Total pesanan", f"{orders['order_id'].nunique():,}".replace(",", "."))
k2.metric("Pendapatan barang", f"BRL {filtered['price'].sum() / 1e6:,.2f} jt")
k3.metric("Rata-rata nilai pesanan", f"BRL {orders['payment_value'].mean():,.0f}")

k4, k5, _ = st.columns(3)
k4.metric("Pesanan terlambat", f"{orders['is_late'].mean() * 100:.1f}%")
k5.metric("Rata-rata skor ulasan", f"{orders['review_score'].mean():.2f} / 5")

st.subheader("Tren pesanan bulanan")
fig, ax = plt.subplots(figsize=(14, 4))
ax.plot(monthly_df.index, monthly_df["jumlah_pesanan"], marker="o", color=MAIN_COLOR, linewidth=2)
ax.set_ylim(0, None)
ax.set_ylabel("Jumlah pesanan")
ax.set_xlabel(None)
sns.despine()
st.pyplot(fig)
plt.close(fig)

tab1, tab2, tab3, tab4 = st.tabs([
    "Kategori Produk (Q1)", "Pengiriman per Wilayah (Q2)", "Segmen Pelanggan (RFM)", "Peta Sebaran",
])

# Tab 1: Pertanyaan 1
with tab1:
    st.markdown(f"**{top_n} kategori dengan pendapatan tertinggi** (harga barang, tanpa ongkir)")
    top = category_df.head(top_n).reset_index()
    colors = [MAIN_COLOR] * 3 + [GREY] * (len(top) - 3)
    fig, ax = plt.subplots(figsize=(12, 0.45 * len(top) + 1))
    sns.barplot(data=top, y="product_category", x="pendapatan", hue="product_category", palette=colors, legend=False, ax=ax)
    for i, (val, pct) in enumerate(zip(top["pendapatan"], top["porsi_%"])):
        ax.text(val, i, f"  {val / 1e3:,.0f} rb ({pct:.1f}%)", va="center", fontsize=9)
    ax.set_xlabel("Pendapatan (ribu BRL)")
    ax.set_ylabel(None)
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x / 1e3:,.0f}"))
    ax.set_xlim(0, top["pendapatan"].max() * 1.22)
    sns.despine(left=True)
    st.pyplot(fig)
    plt.close(fig)

    st.markdown("**Tren pendapatan bulanan 5 kategori teratas**")
    top5 = category_df.head(5).index.tolist()
    trend = (
        filtered[filtered["product_category"].isin(top5)]
        .groupby([filtered["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp(), "product_category"])["price"]
        .sum()
        .unstack()
    )
    fig, ax = plt.subplots(figsize=(14, 4.5))
    for i, cat in enumerate(top5):
        ax.plot(trend.index, trend[cat], marker="o", markersize=3,
                linewidth=2.6 if i == 0 else 1.4, color=MAIN_COLOR if i == 0 else None, label=cat)
    ax.set_ylim(0, None)
    ax.set_ylabel("Pendapatan (ribu BRL)")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x / 1e3:,.0f}"))
    ax.legend(frameon=False, ncol=5, loc="upper left")
    sns.despine()
    st.pyplot(fig)
    plt.close(fig)

    st.info(
        " Pendapatan didominasi `health_beauty` dan `watches_gifts`,"
        "dengan penjualan semua kategori meningkat saat Black Friday (November 2017)."
    )

# Tab 2: Pertanyaan 2
with tab2:
    min_orders = st.slider("Tampilkan state dengan minimal jumlah pesanan", 0, 500, 30, step=10)
    state_plot = state_df[state_df["jumlah_pesanan"] >= min_orders].sort_values("persen_terlambat", ascending=False).reset_index()
    nat_late = orders["is_late"].mean() * 100
    highlight = [ALERT if v >= 2 * nat_late else GREY for v in state_plot["persen_terlambat"]]

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**% pesanan terlambat per state** (merah = ≥ 2× rata-rata nasional)")
        fig, ax = plt.subplots(figsize=(7, 0.32 * len(state_plot) + 1))
        sns.barplot(data=state_plot, y="customer_state", x="persen_terlambat", hue="customer_state", palette=highlight, legend=False, ax=ax)
        ax.axvline(nat_late, color="black", linestyle="--", linewidth=1, label=f"Nasional {nat_late:.1f}%")
        ax.set_xlabel("% diterima melewati estimasi")
        ax.set_ylabel(None)
        ax.legend(frameon=False, loc="lower right")
        sns.despine(left=True)
        st.pyplot(fig)
        plt.close(fig)
    with col2:
        st.markdown("**Rata-rata lama pengiriman per state**")
        fig, ax = plt.subplots(figsize=(7, 0.32 * len(state_plot) + 1))
        sns.barplot(data=state_plot, y="customer_state", x="rata2_hari_kirim", hue="customer_state", palette=highlight, legend=False, ax=ax)
        ax.axvline(orders["delivery_days"].mean(), color="black", linestyle="--", linewidth=1)
        ax.set_xlabel("Hari sejak pembelian sampai diterima")
        ax.set_ylabel(None)
        sns.despine(left=True)
        st.pyplot(fig)
        plt.close(fig)

    st.markdown("**Dampak keterlambatan dan lama kirim terhadap skor ulasan**")
    orders_bin = orders.assign(
        kelompok=pd.cut(orders["delivery_days"], bins=[0, 7, 14, 21, 30, np.inf],
                        labels=["≤ 7 hari", "8–14 hari", "15–21 hari", "22–30 hari", "> 30 hari"])
    )
    late_score = orders.groupby("is_late")["review_score"].mean().rename({False: "Tepat waktu", True: "Terlambat"})
    bin_score = orders_bin.groupby("kelompok", observed=True)["review_score"].mean()

    col3, col4 = st.columns([1, 1.6])
    with col3:
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.bar(late_score.index, late_score.values, color=[MAIN_COLOR, ALERT][: len(late_score)])
        for i, v in enumerate(late_score.values):
            ax.text(i, v + 0.08, f"{v:.2f}", ha="center", fontweight="bold")
        ax.set_ylim(0, 5)
        ax.set_ylabel("Rata-rata skor ulasan (1–5)")
        sns.despine()
        st.pyplot(fig)
        plt.close(fig)
    with col4:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(bin_score.index.astype(str), bin_score.values,
               color=[MAIN_COLOR if v >= 4 else ALERT for v in bin_score.values])
        for i, v in enumerate(bin_score.values):
            ax.text(i, v + 0.08, f"{v:.2f}", ha="center")
        ax.set_ylim(0, 5)
        ax.set_xlabel("Lama pengiriman")
        sns.despine()
        st.pyplot(fig)
        plt.close(fig)

    st.info(
        "Pengiriman sering terlambat di AL, MA, SE, CE, dan PI. "
        "Skor ulasan lebih dipengaruhi ketepatan waktu barang sampai daripada kecepatan pengiriman."
    )
    with st.expander("Lihat tabel per state"):
        st.dataframe(state_df.sort_values("persen_terlambat", ascending=False).round(2), width="stretch")

# Tab 3: RFM
with tab3:
    c1, c2, c3 = st.columns(3)
    c1.metric("Rata-rata recency", f"{rfm_df['recency'].mean():.0f} hari")
    c2.metric("Pelanggan belanja > 1 kali", f"{(rfm_df['frequency'] > 1).mean() * 100:.1f}%")
    c3.metric("Rata-rata monetary", f"BRL {rfm_df['monetary'].mean():,.0f}")

    seg = rfm_df.groupby("segment").agg(pelanggan=("frequency", "count"), belanja=("monetary", "sum"))
    seg["% pelanggan"] = seg["pelanggan"] / seg["pelanggan"].sum() * 100
    seg["% belanja"] = seg["belanja"] / seg["belanja"].sum() * 100
    seg = seg.sort_values("% pelanggan")

    fig, ax = plt.subplots(figsize=(12, 4.5), dpi=100)
    y = np.arange(len(seg))
    ax.barh(y + 0.2, seg["% pelanggan"], height=0.4, color=GREY, label="% pelanggan")
    ax.barh(y - 0.2, seg["% belanja"], height=0.4, color=MAIN_COLOR, label="% total belanja")
    for i, (p, b) in enumerate(zip(seg["% pelanggan"], seg["% belanja"])):
        ax.text(p + 0.4, i + 0.2, f"{p:.1f}%", va="center", fontsize=9, color="dimgray")
        ax.text(b + 0.4, i - 0.2, f"{b:.1f}%", va="center", fontsize=9, color=MAIN_COLOR)
    ax.set_yticks(y)
    ax.set_yticklabels(seg.index)
    ax.set_xlabel("Persentase (%)")
    ax.legend(frameon=False, loc="lower right")
    sns.despine(left=True)
    st.pyplot(fig)
    plt.close(fig)

    with st.expander("Aturan segmen"):
        st.markdown(
            "- **R** (1–4): kuartil recency, 4 = paling baru belanja · **F** (1–3): 1×, 2×, ≥3× · "
            "**M** (1–4): kuartil total belanja\n"
            "- Pelanggan Setia: F ≥ 2 & R ≥ 3 · Setia tapi Mulai Pasif: F ≥ 2 & R ≤ 2\n"
            "- Pelanggan Bernilai Tinggi Baru: F = 1, M = 4, R ≥ 3 · Pelanggan Baru: F = 1, M < 4, R ≥ 3\n"
            "- Pelanggan Bernilai Tinggi Tidur: F = 1, M = 4, R ≤ 2 · Pelanggan Tidur: F = 1, M < 4, R ≤ 2"
        )
    st.info(
        "Sebagian besar pelanggan hanya berbelanja sekali."
        "Segmen Pelanggan Bernilai Tinggi adalah target utama program retensi.")

# Tab 4: Peta
with tab4:
    st.markdown("**Pendapatan per state** - ukuran lingkaran = pendapatan, merah = keterlambatan ≥ 2× nasional")
    map_df = state_df.reset_index().merge(geo_state_df, on="customer_state", how="inner")
    peta = folium.Map(
        location=[-14.5, -51], zoom_start=4,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri",
    )
    max_rev = map_df["pendapatan"].max()
    for _, row in map_df.iterrows():
        folium.CircleMarker(
            location=[row["lat"], row["lng"]],
            radius=4 + (row["pendapatan"] / max_rev) ** 0.5 * 30,
            color=ALERT if row["persen_terlambat"] >= 2 * nat_late else MAIN_COLOR,
            fill=True,
            fill_opacity=0.6,
            tooltip=(f"{row['customer_state']}: BRL {row['pendapatan']:,.0f} · "
                     f"{row['jumlah_pesanan']:,} pesanan · terlambat {row['persen_terlambat']:.1f}%"),
        ).add_to(peta)
    st_folium(peta, height=520, use_container_width=True, returned_objects=[])

st.caption("Proyek Analisis Data Dicoding")
