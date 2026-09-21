# `cas_artifact` - a real BuildStream CAS, two artifacts

`UX-907`. Not hand-written protos: `buildbox-casd` from the BuildStream
2.8.0 wheel captured two directory trees and wrote the `Artifact` protos
beside them, and only the non-empty object shards were copied out (casd
pre-creates all 256).

```text
buildstream==2.8.0 (cp311 manylinux wheel), buildbox-casd bundled
CASCache.import_directory -> CaptureTree, then Artifact{version, build_success,
strong_key, files} serialised to artifacts/refs/lab/<element>/<key>
```

Two elements in project `lab`, chosen so every case the walk has to get
right is in 2 KB. Every byte below is the proto's own, and the two
totals are the sum of these columns:

```text
base  b1a5e0...cafe                          app   a99f00...beef
  /             dir proto  78                  /             dir proto  78
  usr/          dir proto 155                  usr/          dir proto 154
    bin/        dir proto 162                    bin/        dir proto  77
      tool           file   5                      app            file  45
      tool-alias     file   5  <- same blob       lib/        dir proto  86  <- same blob
    lib/        dir proto  86                       libshared.so file  23  <- same blob
      libshared.so   file  23
                        = 509                                        = 463
```

- `tool` and `tool-alias` are one blob, so `base` weighs 509 and not 514:
  a file staged twice costs once.
- `app` and `base` share `libshared.so` (23) and the `usr/lib` directory
  proto that holds it (86). Each artifact carries all 109 - it would need
  them alone - so the rows sum to 972 while the cache holds 863.

`tests/unit/test_an_artifact_has_a_weight.py` reads it.
