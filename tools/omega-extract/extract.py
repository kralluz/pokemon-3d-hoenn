"""Decifra o asset pack, desempacota os .7z e grava os AssetBundles (.ab)."""
import base64, io, json, math, os, shutil, sys, tempfile, time
sys.path.insert(0, os.path.dirname(__file__))
import omega, py7zr

ROOT  = sys.argv[1] if len(sys.argv) > 1 else r"apk/_extracted/pack/assets"
OUT   = sys.argv[2] if len(sys.argv) > 2 else r"apk/_extracted/out/bundles"
LIMIT = int(sys.argv[3]) if len(sys.argv) > 3 else 0

def fast_decrypt(data, name):
    pb = base64.b64encode(name.encode()); L = len(pb)
    rk = bytes(pb[i] ^ data[i] ^ omega.F[i % 14] for i in range(L))
    body = data[L + 4:]
    P = math.lcm(L, 14)
    ks = bytes(rk[j % L] ^ omega.F[(L + j) % 14] for j in range(P))
    n = len(body)
    tiled = (ks * (n // P + 1))[:n]
    return (int.from_bytes(body, "big") ^ int.from_bytes(tiled, "big")).to_bytes(n, "big")

mapping = sorted(json.load(open(os.path.join(os.path.dirname(__file__), "abmap.json"))).items())
if LIMIT: mapping = mapping[:LIMIT]
os.makedirs(OUT, exist_ok=True)
tmp = tempfile.mkdtemp(prefix="omega7z")
t0 = time.time(); ok = nfiles = nbytes = 0; errs = []
for i, (rel, name) in enumerate(mapping, 1):
    try:
        data = open(os.path.join(ROOT, rel), "rb").read()
        with py7zr.SevenZipFile(io.BytesIO(fast_decrypt(data, name))) as z:
            work = os.path.join(tmp, "w"); shutil.rmtree(work, ignore_errors=True)
            z.extractall(path=work)
        dst = os.path.join(OUT, name.replace("/", os.sep) + ".ab")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        got = [os.path.join(dp, x) for dp, _, fn in os.walk(work) for x in fn]
        if len(got) == 1:
            nbytes += os.path.getsize(got[0]); shutil.move(got[0], dst); nfiles += 1
        else:                                    # 7z com varios arquivos: vira pasta
            d2 = dst[:-3]; os.makedirs(d2, exist_ok=True)
            for g in got:
                nbytes += os.path.getsize(g)
                shutil.move(g, os.path.join(d2, os.path.basename(g))); nfiles += 1
        ok += 1
    except Exception as e:
        errs.append((name, f"{type(e).__name__}: {e}"))
    if i % 250 == 0:
        print(f"  {i}/{len(mapping)}  ok={ok}  erros={len(errs)}  "
              f"{nbytes/1e6:.0f} MB  {time.time()-t0:.0f}s", flush=True)
shutil.rmtree(tmp, ignore_errors=True)
print(f"\nconcluido: {ok}/{len(mapping)} bundles | {nfiles} arquivos | "
      f"{nbytes/1e6:.0f} MB | {time.time()-t0:.0f}s")
for e in errs[:15]: print("  ERRO", e)
