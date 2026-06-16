## **Product Requirement Document (PRD)** 

|**Nama Project**|CLI Automated Media Backup Tool (Python Version)|
|---|---|
|**Status**|Progres Pengembangan / Spesifikasi Baru|
|**Target Pengguna**|Pengguna PC/Laptop Windows yang ingin mencadangkan foto & video dari<br>HP secara nirkabel/kabel secara otomatis, transparan, dan menyeluruh tanpa<br>konfigurasi manual.|



## **1. Latar Belakang & Tujuan** 

Proses pemindahan data media (foto dan video) dari ponsel pintar (HP) ke komputer sering kali menghadapi kendala efisiensi jika dilakukan secara manual melalui File Explorer bawaan sistem operasi. Masalah utama meliputi lambatnya pemindaian folder terfragmentasi, risiko duplikasi data, serta keharusan pengguna untuk terus memeriksa apakah perangkat sudah terdeteksi dengan benar sebelum memulai transfer. 

Dokumen ini merinci kebutuhan untuk membangun perangkat lunak berbasis **Command Line Interface (CLI)** menggunakan bahasa pemrograman **Python** . Aplikasi ini dirancang untuk mendeteksi perangkat secara otomatis (Plug-and-Play), memindai seluruh direktori penyimpanan internal HP secara menyeluruh (tidak terbatas pada folder kamera/DCIM), menyaring file media berdasarkan ekstensi, dan memindahkannya ke komputer secara inkremental dengan visualisasi _progress bar_ yang informatif. 

## **2. Fitur Utama (Features)** 

- **Auto-Detection & Connection Polling (Hot-Plug):** Program tidak akan langsung berhenti (crash/exit) jika HP belum terhubung. Sebaliknya, program memasuki mode _polling_ (menunggu secara aktif) hingga mendeteksi adanya _Drive Letter_ baru yang valid dari koneksi USB HP (MTP/Mass Storage Mode). 

- **Full-Disk Directory Scanning (Deep Scan):** Berbeda dengan sistem pencadangan konvensional yang hanya menyasar folder `DCIM/Camera` , fitur ini akan menyisir seluruh struktur pohon folder di penyimpanan HP untuk mencari media tersembunyi (misal: folder unduhan, aplikasi pesan instan, tangkapan layar, dll). 

- **Media Filtering Otomatis:** Menyaring berkas secara otomatis berdasarkan ekstensi file media populer yang ditentukan dalam konfigurasi (contoh: `.jpg` , `.jpeg` , `.png` , `.mp4` , `.mov` , `.mkv` ). 

- **Two-Phase Execution (Scan & Display First):** Membagi proses eksekusi menjadi dua tahap konkrit. Tahap pertama melakukan kalkulasi dan menampilkan jumlah total berkas baru yang ditemukan, memberikan transparansi penuh sebelum operasi penulisan disk dimulai. 

- **Incremental Smart Backup:** Membandingkan metadata nama file antara penyimpanan ponsel dan komputer. Hanya berkas baru yang belum ada di direktori tujuan PC yang akan diproses, menghemat waktu transfer dan ruang penyimpanan. 

- **Real-time Progress Bar & Chunk-based Copying:** Menampilkan indikator kemajuan visual piringan dinamis dan persentase numerik (0% - 100%) untuk setiap file individual yang sedang ditransfer, mencegah ketidakpastian visual (kesan aplikasi membeku) saat mentransfer file video berukuran besar. 

1 

## **3. Alur Pengguna (User Flow)** 

1. User membuka terminal (CMD/PowerShell) dan mengeksekusi program Python. 

2. **Fase Idle/Menunggu:** Program mendeteksi bahwa HP belum tercolok, menampilkan pesan tunggu `[IDLE] Menunggu HP terhubung via kabel USB...` secara berkala di layar terminal. 

3. User menghubungkan HP ke PC via kabel USB dan memastikan mode koneksi diatur ke **"File Transfer / MTP"** . 

4. **Fase Deteksi Otomatis:** Program menangkap kehadiran drive penyimpanan HP baru secara instan dan otomatis melanjutkan ke tahap berikutnya tanpa intervensi user. 

5. **Fase Deep Scan:** Program melakukan _scanning_ ke seluruh folder root di dalam penyimpanan ponsel untuk mengompilasi daftar media yang sesuai kriteria. 

6. **Fase Rangkuman:** Program menampilkan total kuantitas berkas baru yang siap dicadangkan ke layar. 

7. **Fase Transfer Data:** Proses penyalinan berjalan secara sekuensial. Layar CLI memperbarui baris kemajuan (*progress bar*) secara dinamis berlandaskan ukuran bita (*bytes*) yang berhasil dikirim ke PC. 

8. Program selesai, menampilkan laporan sukses, dan kembali ke mode aman. 

## **4. Spesifikasi Teknis & Kebutuhan Non-Fungsional** 

|**Parameter**|**Spesifikasi Kebutuhan**|
|---|---|
|**Bahasa Pemrograman**|Python 3.8 ke atas.|
|**Antarmuka (UI)**|Command Line Interface (CLI) dengan dukungan karakter ANSI untuk<br>_progress bar_.|
|**Mekanisme Copying**|Berbasis_buffer stream_(pembacaan blok bita per bita menggunakan<br>`os.open`atau<br>`shutil`kustom) untuk kalkulasi presisi_progress bar_.|
|**Kompatibilitas OS**|Windows 10 / Windows 11 (Utama, memanfaatkan pemetaan huruf<br>drive logis).|
|**Dependensi Pihak Ketiga**|Nol (_Zero-dependency_). Program hanya menggunakan pustaka standar<br>bawaan Python (<br>`os`,<br>`sys`,<br>`time`,<br>`shutil`) untuk menjamin<br>portabilitas tinggi tanpa perlu<br>`pip install`.|



## **5. Aturan Konfigurasi Sistem (User Configuration Block)** 

Aplikasi menyediakan blok variabel statis di bagian atas skrip agar mudah disesuaikan oleh pengguna sebelum dijalankan: 

- `TARGET_DRIVE_NAME` : String pencarian kata kunci untuk mengenali penyimpanan HP (misal: 

- penyimpanan internal). 

2 

- `PC_BACKUP_DIR` : Lokasi absolut direktori penyimpanan di komputer (Contoh: `D:` 

- `\Backup_Media_HP` ). 

- `VALID_EXTENSIONS` : Tuple berisi daftar ekstensi format berkas yang diizinkan untuk diproses oleh 

- sistem filtrasi. 

3
