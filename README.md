<<<<<<< HEAD
# Sensor Suhu Terdistribusi: MQTT vs REST

Kode praktikum Sistem Terdistribusi, dimodifikasi dari kode dosen sesuai Langkah 1 LKM.
Panduan lengkap per anggota ada di dokumen panduan kelompok.

## Struktur
```
logutil.py            utilitas log CSV + penjadwalan run (dipakai semua skrip)
REST/server.py        server Flask: POST /data (terima), GET /data (polling konsumen)
REST/client.py        node pengirim REST (loop periodik, tanpa retry)
REST/poller.py        konsumen REST untuk Blok E (polling)
MQTT/pub.py           node pengirim MQTT (QoS, antrean offline, RTT via echo)
MQTT/sub.py           konsumen MQTT (sesi persisten, --echo hanya di 1 subscriber)
MQTT/.env.example     contoh kredensial -> salin jadi MQTT/.env (jangan di-commit)
tools/check_clock.py  cek selisih jam terhadap NTP (< 50 ms)
tools/monitor_cpu.py  ukur CPU server/broker (Blok E)
tools/mosquitto_local.conf  broker lokal opsional untuk Blok E
analysis/analyze.py   log mentah -> per_run.csv, ringkasan.csv, grafik
```

## Instalasi
```
pip install -r requirements.txt
```

## Perintah cepat
```
# laptop server (Nova)
python REST/server.py
python MQTT/sub.py --consumer main --echo --quiet

# laptop node (ganti --node dan IP server)
python REST/client.py --node johan --url http://IP_NOVA:5151 --exp B_N4 --runs 10 --duration 60 --gap 10 --interval 0.2 --start-at 14:30
python MQTT/pub.py   --node johan --exp B_N4 --runs 10 --duration 60 --gap 10 --interval 0.2 --qos 1 --start-at 14:45

# analisis (setelah semua folder logs/ dikumpulkan ke logs_all/<nama>/)
python analysis/analyze.py --logs logs_all --out hasil
```

## Skema log
Kolom LKM (`timestamp_iso, node_id, protocol, t_send_ms, t_recv_ms, payload_bytes, suhu, sequence_no`)
ditambah `exp` (label kondisi), `run`, `status`, dan `rtt_ms`.
Latensi utama memakai RTT sehingga tidak bergantung pada sinkronisasi jam;
latensi satu arah (`oneway`) juga dihitung untuk dipakai jika jam sudah tersinkron.
=======
# Sistem Terdistribusi (Distributed Systems)

Repositori ini memuat tugas dan implementasi untuk mata kuliah **Sistem Terdistribusi**.

---

## 👥 Anggota Kelompok

| No | Nama Lengkap | NIM |
|:--:|:-------------|:---:|
| 1 | **Rahma Aliyyah** | `2646000119` |
| 2 | **Johan Arizona** | `2646000125` |
| 3 | **Nofa Nisrina Salsabila** | `2646000117` |
| 4 | **Ketut Bagus Wedanta A.M.** | `2646000123` |

---

## 🌿 Struktur Branch & Repositori

Branch `main` ini difungsikan khusus sebagai halaman informasi kelompok dan dokumentasi repositori.

Seluruh kode program, kode tugas, serta implementasi materi dari masing-masing anggota berada di **branch masing-masing**.

### Cara Berpindah ke Branch Terkait

Untuk melihat maupun menjalankan implementasi kode, silakan beralih ke branch yang bersangkutan:

```bash
# Melihat daftar seluruh branch yang ada
git branch -a

# Berpindah ke branch yang diinginkan
git switch <nama-branch>
# atau
git checkout <nama-branch>
```

---
*Fakultas Ilmu Komputer (FILKOM) — Universitas Brawijaya*
>>>>>>> 24411e3ddec592b78ca355d138be39b8acde6116
