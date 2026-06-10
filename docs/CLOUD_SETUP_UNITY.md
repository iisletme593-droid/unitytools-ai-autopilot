# Bulut GPU Makinesinde UnityTools Kurulumu (Unity odaklı)

Yerel PC (Intel HD 4600, ayrık GPU yok, 8 GB RAM) Unity'nin HDRP sahnelerini ve
UnityTools autopilot'unu kaldırmıyor. Çözüm: **ayrık GPU'lu bir bulut Windows makinesi**
kiralayıp Unity Editor + UnityTools'u oraya kurmak ve uzaktan bağlanmak.

> **Karar (2026-06-10):** Kullanıcının AB adres/ödeme erişimi yok (Shadow PC eleniyor),
> ayda < 40 saat kullanım, ~€50/ay tavan. Bu yüzden hedef: **ülke kısıtı olmayan, SAATLİK,
> A4500'den güçlü** bir makine. Birincil öneri **airgpu (L40S)**; daha ucuz/teknik alternatif
> **TensorDock (RTX 4090)**. Gerekli GPU barı: **RTX A4500 (20GB) veya üstü** — A4000 16GB ve
> Shadow Neo tier'ı bunun altında, seçme.

> **IBM Quantum bu iş için kullanılamaz.** O bir kuantum-devre API servisidir; üzerine
> Unity/Unreal kurulamaz, klasik işleri hızlandırmaz. `QUANTUM_IBM` token'ı yalnızca
> Qiskit işleri için anlamlıdır (ayrı, opsiyonel bir özellik).

---

## 1. Mimari: her şey tek makinede

En basit ve en güvenli model — **Unity Editor + UnityTools çekirdeği + LLM hepsi bulut
makinesinde** çalışır; sen sadece uzak masaüstüyle bağlanırsın:

```
[Senin zayıf PC'in]  --uzak masaüstü (Parsec/Shadow client/RDP)-->  [Bulut Windows + GPU]
                                                                      ├─ Unity Editor (+ UnityTools paneli)
                                                                      ├─ unitytools chat-server  (127.0.0.1:7778)
                                                                      ├─ Unity bridge            (127.0.0.1:7777)
                                                                      └─ LLM (Anthropic API ya da yerel Ollama)
```

Hepsi tek kutuda olduğu için tüm trafik **loopback (127.0.0.1)** kalır → `UNITYTOOLS_ALLOW_REMOTE`
gerekmez, LAN'a hiçbir şey açılmaz. (Az önce eklediğimiz token auth yine de devrede.)

---

## 2. Bulut makinesini seç (saatlik, ülke kısıtsız)

Güncel araştırma (2026-06-10, fiyatlar değişebilir):

- **airgpu** (airgpu.com) — *birincil öneri.* AB veri merkezleri (Frankfurt vb.), **ülke
  kısıtı yok**, tam Windows, **Parsec/Moonlight** ile editör-kalitesinde yayın.
  - **L40S 48GB — $1.20/saat** (≈RTX 4080, A4500'den net güçlü) ← öneri.
  - A10G 24GB — $1.05/saat (A4500 civarı; HDRP viewport'ta sınırda kalabilir).
  - Kalıcı disk: 50GB başına $3.50/ay (HDRP için ~150-250GB = $10.5-17.5/ay; GPU kapalıyken
    de ödenir).
  - ~30 saat/ay × $1.20 + ~$10 disk ≈ **$46/ay** → €50 tavanına sığar.
- **TensorDock** (tensordock.com) — *en ucuz + en güçlü, ama DIY.* **RTX 4090 24GB ~$0.37/saat**
  (A4500'ün ~2 katı), ülke kısıtı yok, AB konumları. ~35 saat ≈ **$13 + ~$4 disk ≈ $17/ay**.
  Karşılığında: kendi **Windows lisansını** getirirsin (ya da aktivasyonsuz Windows — çalışır)
  ve Parsec'i kendin kurarsın (aşağıda birlikte yaparız). Pazar yeri olduğu için host
  güvenilirliği değişir.

> **Kaçın (Windows Unity Editor ÇALIŞTIRAMAZ):** RunPod, Vast.ai, Lambda (Linux/konteyner),
> Paperspace (Tem-2024'ten beri yeni hesaba Windows kapalı). Shadow PC turnkey ve A4500'ü
> €50/ay verir ama **Türkiye desteklenmiyor** (AB adres/ödeme şart).

Minimum GPU barı: **RTX A4500 20GB veya üstü** (A5000 / RTX 4000 Ada / A10G / L40S / 3090 /
4090). **A4000 16GB seçme** — A4500'den aşağı.

---

## 3. Bulut makinesinde ön gereksinimler

Uzak masaüstüyle bağlandıktan sonra, bulut makinesinde:

1. **GPU sürücüsü** güncel olsun (NVIDIA/AMD — Shadow/Paperspace genelde hazır gelir).
2. **Git**: https://git-scm.com/download/win
3. **Python 3.11** (3.10–3.12 olur): https://www.python.org/downloads/  → kurulumda
   "Add python.exe to PATH" işaretle.
4. **Unity Hub + Unity Editor**: https://unity.com/download → Hub'ı kur, bir LTS sürüm
   (ör. 2022 LTS / 6000 LTS) indir, hesabınla giriş yap (Personal lisans ücretsiz).

---

## 4. UnityTools'u makineye kur

> Eklenti kurulumu yalnızca **kaynak checkout'tan** çalışır (wheel'de paketlenmez).
> Bu yüzden repoyu klonla ve editable kur.

PowerShell'de:

```powershell
git clone https://github.com/iisletme593-droid/unitytools-ai-autopilot.git
cd unitytools-ai-autopilot
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

> Not: repodaki mevcut `.venv` bozuk (silinmiş bir profile işaret ediyor). Bulut
> makinesinde **yeni** venv oluşturduğun için sorun olmaz.

`.env` dosyasını oluştur (`.env.example`'ı kopyala) ve şunları ayarla:

```ini
# Sağlayıcı: kalite için anthropic (API key ister) ya da yerel/ücretsiz ollama
UNITYTOOLS_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Güvenlik token'ı (üç süreç de aynı değeri görmeli)
UNITYTOOLS_BRIDGE_TOKEN=uzun-rastgele-bir-deger

UNITY_BRIDGE_PORT=7777
```

Token'ın Unity Editor tarafından da görülmesi için **Windows kullanıcı ortam değişkeni**
olarak da ayarla (bir kez):

```powershell
setx UNITYTOOLS_BRIDGE_TOKEN "uzun-rastgele-bir-deger"
```
(setx sonrası yeni açılan terminaller/Unity bunu görür.)

Doğrula:

```powershell
unitytools doctor
unitytools status
```

### LLM sağlayıcı seçimi
- **Anthropic (önerilen):** en iyi tool-calling kalitesi; `ANTHROPIC_API_KEY` + kullanım ücreti.
- **Ollama (ücretsiz/offline):** bulut GPU yeterince güçlüyse. https://ollama.com kur,
  `ollama pull qwen2.5:14b-instruct`, `.env`'de `UNITYTOOLS_PROVIDER=ollama`.

---

## 5. Unity eklentisini projene kur

Bir Unity projesi aç (Hub'dan yeni proje ya da mevcut projen), sonra:

```powershell
unitytools install-unity-plugin --project "C:\Yol\UnityProjesi"
```

Bu, panel + bridge + Autopilot script'lerini projeye kopyalar. Unity projeyi yeniden
derleyince `BridgeServer` otomatik başlar ve (yeni güvenlik koduyla) token'ı `.env`/ortamdan
okur.

---

## 6. Çalıştır

1. Unity Editor'de projeyi aç (bridge otomatik dinlemeye başlar: 127.0.0.1:7777).
2. Sohbet sunucusunu başlat (panel kendisi de başlatabilir; manuel de olur):
   ```powershell
   unitytools chat-server --engine unity
   ```
   Açılışta `Auth: ON (token required)` görmelisin.
3. Unity'de: **Tools > UnityTools > Open Chat** → **Connect**. Panel token'ı otomatik gönderir.
4. Artık autopilot Unity sahnesini sürebilir.

---

## 7. Güvenlik durumu

- Her şey tek makinede ve loopback → dışarıya açık yüzey yok.
- Token auth devrede: editör paneli ile Python tarafı aynı `UNITYTOOLS_BRIDGE_TOKEN`'ı
  kullanır.
- **Loopback dışına ASLA token'sız açma.** Gerekirse (hibrit senaryo) önce VPN/SSH tüneli
  kur, sonra `UNITYTOOLS_ALLOW_REMOTE=1` + güçlü token. Düz internete `--host 0.0.0.0`
  açma; kod zaten token'sız bunu reddediyor.

---

## 8. Sorun giderme

- `unitytools doctor` / `status` — sağlayıcı + bridge tanılaması.
- Panel "Unauthorized" hatası → editör tarafı token'ı görmüyor; `setx` ile ayarlayıp
  Unity'yi yeniden başlat (ve eklentiyi güncel sürümle yeniden kur).
- Takılı eski sunucu süreçleri → `unitytools cleanup-processes`.
- Unity bridge testi → `unitytools unity-ping`.

---

## (Opsiyonel) Hibrit model — autopilot yerelde, motor bulutta

Daha ileri/teknik. Unity + bridge bulutta; `unitytools` çekirdeğini yerelde çalıştırıp
uzak bridge'e bağlanmak istersen: bulut ile yerel arasında **VPN ya da SSH tüneli** kur
(7777/7778 portlarını tünelle), bulut tarafında `UNITYTOOLS_ALLOW_REMOTE=1` + token ayarla.
Tünel kullanıldığında trafik yine loopback üzerinden taşınır. Çoğu kullanım için Bölüm 1'deki
"her şey tek makinede" modeli daha basit ve güvenlidir.
