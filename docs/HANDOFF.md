# Proje Durumu / Handoff (2026-06-10)

> Bu dosya, işi başka bir makinede (ör. AWS bulut GPU kutusu) sürdüren yeni bir
> Claude Code oturumu veya geliştirici için bağlam özetidir. Sohbet geçmişi makineler
> arası taşınmaz; bu repo + bu doküman taşınır.

## Amaç
`unitytools` = Unity (ve Unreal) Editor'ü süren yerel-öncelikli bir AI autopilot. Kullanıcının
yerel PC'si (Intel HD 4600, GPU yok) ağır Unity/HDRP işini kaldırmıyor → iş **bulut GPU Windows
makinesine** taşınıyor. Hedef motor: **Unity** (Unreal değil, şimdilik).

## Bulut planı
- Sağlayıcı: **AWS EC2**, kullanıcının kredisi var (~2 ay). Bölge **us-east-1** (hesap 641150855049).
- Instance: **g5.2xlarge** (A10G 24GB, 8 vCPU, 32GB RAM), Windows Server 2025.
- **Maliyet kuralı:** iş bitince **Stop** et (sadece EBS ~$12/ay yazar). LLM için Anthropic API
  kullan (yerel Ollama çalıştırma — RAM/GPU Unity'de kalsın).
- ⚠️ **Instance store (450GB NVMe) geçicidir — Stop'ta silinir.** Unity/proje **C: (EBS)** üzerine.
- Ayrıntılı kurulum: bkz. [CLOUD_SETUP_UNITY.md](CLOUD_SETUP_UNITY.md).

## Şu an bekleyen tek engel: vCPU kotası
- "Running On-Demand G and VT instances" kotası **0** → g5.2xlarge açılmıyor.
- **Kota artış talebi (8) açıldı**, durum **CASE_OPENED** (AWS manuel inceliyor). Talep id:
  `c7c0628dd08f4dc6a4f758e6603df433PhIQHaxq`. Durum: Service Quotas → Quota request history.
- Onaylanınca (aktif kota 8 olunca) launch çalışır, kuruluma geçilir.

## Makinede kurulum sırası (kota onaylanınca)
> Kestirme: aşağıdaki 2-5 adımlarını `scripts/setup_windows.ps1` otomatik yapar:
> `irm https://raw.githubusercontent.com/iisletme593-droid/unitytools-ai-autopilot/<dal>/scripts/setup_windows.ps1 | iex`

1. NVIDIA sürücü → NICE DCV veya Parsec ile bağlan.
2. Python 3.11 + Unity Hub/Editor (LTS).
3. `git clone https://github.com/iisletme593-droid/unitytools-ai-autopilot.git` →
   `py -3.11 -m venv .venv` → `.\.venv\Scripts\Activate.ps1` → `pip install -e .`
   (Repo `.venv`'i bozuk; makinede YENİ venv kur.)
4. `.env`: `UNITYTOOLS_PROVIDER=anthropic` + `ANTHROPIC_API_KEY` + `UNITYTOOLS_BRIDGE_TOKEN`
   (uzun rastgele). Token'ı `setx UNITYTOOLS_BRIDGE_TOKEN "..."` ile kullanıcı env'ine de koy
   (Unity paneli + Python aynı token'ı görsün).
5. `unitytools install-unity-plugin --project "C:\...UnityProjesi"`.
6. Claude Code'u kur: `irm https://claude.ai/install.ps1 | iex` → `claude` (Pro/Max girişi veya
   ANTHROPIC_API_KEY). `cd unitytools-ai-autopilot` → `claude`.
7. Unity'de projeyi aç → `unitytools chat-server --engine unity` → panelde Connect.

## Güvenlik (bu oturumda yapıldı — ÖNEMLİ notlar)
- **Kimlik doğrulamasız RCE zinciri kapatıldı:** chat-server + Unity/Unreal köprüleri artık
  paylaşılan token (`UNITYTOOLS_BRIDGE_TOKEN`→`UNITYTOOLS_SECRET`→`UNITYTOOLS_KEY`) ister,
  loopback zorlanır; `ImportAsset`/`import_asset` path containment; menu/component allow-list.
  Yeni modül: `unitytools/core/security.py`. Python tarafı test edildi (38 test geçiyor).
- ⚠️ **Editör tarafı için Unity eklentisini YENİDEN KUR** (`install-unity-plugin`) — C# değişikliği
  ancak o zaman derlenir/devreye girer.
- ⚠️ **AWS admin anahtarını ROTATE et:** `cboinn-temp-admin` access key'i düz metin halde
  `D:\Adnan\NewPC\D` altında onlarca `.env`/yedekte duruyor (admin = tüm hesap kontrolü). IAM'den
  sil/yenile. Genel olarak o ağaçta ciddi sır dağınıklığı var (AWS, Binance/BingX, Shopier, OpenAI).
- ✅ (2026-06-12) Yüksek öncelikli **kararlılık hataları düzeltildi**:
  - **Anthropic 400 kilidi**: 400 gelince history onarılıyor (yetim tool_use/tool_result,
    boş content) ve istek bir kez tekrarlanıyor; hâlâ 400 ise bozuk tur geçmişten geri
    alınıyor — sohbet artık kalıcı kilitlenmiyor (`orchestrator.py`).
  - **RPC yanıt korelasyonu**: Unity/Unreal bridge'leri yanıtları artık `id` ile eşliyor;
    timeout sonrası geç gelen yanıtlar atılıyor, buffer bağlantılar arası sızmıyor.
  - **Build kıran guard'lar**: Unreal runtime'da `GetActorLabel` → `GetName`;
    `GeneratedAssetLoader.cs` `#if UNITY_EDITOR` ile sarıldı.
  - **Mojibake**: repo genelinde (Python/C#/MD, 25+ dosya) bozuk Türkçe + ok/emoji
    karakterleri onarıldı.
  - Testler: 41/41 geçiyor (bridge korelasyonu ve 400 kilidi için yeni regresyon testleri).

## Test çalıştırma
Repo `.venv` bozuk. Geçici ortamla:
`uv run --no-project --with pydantic --with python-dotenv --with anthropic --with rich --with prompt_toolkit --with pytest python -m pytest tests/ -q -p no:cacheprovider`
