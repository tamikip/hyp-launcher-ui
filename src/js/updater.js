/* ============================================================
   增量更新客户端

   和 tools/sim/pack.py 配套。整体流程：

     1. loadGear(url)   加载 gear 表（CDC 分块用，必须与打包器一致）
     2. localIndex()    把本地已安装的文件按同样策略分块、算 hash，
                        得到"我手上已有哪些 chunk" + 逐文件 sha256
     3. check(url)      拉 latest.json -> v2 manifest
     4. plan()          对比两边，算出要下的 chunk（去重）、要删的文件
     5. apply()         并发下载 -> 逐块校验 -> 按偏移拼装 ->
                        逐文件校验 sha256 -> 产出可写盘的结果
     6. 断点续传：已下好的 chunk 留在一个 have 集合里，重入时自动跳过
        暂停/失败重试也都在这一层

   浏览器里没有文件系统，所以 apply() 返回 {path: Uint8Array}；
   接进 WebView2 时把最后一步换成把 chunk 交给宿主落盘即可，
   前面"该下哪些块"的逻辑完全一样。
   ============================================================ */

(function () {
  'use strict';

  var GEAR = null;      // Uint32Array(256) 低位
  var GEAR_HI = null;   // Uint32Array(256) 高位

  function hex(buf) {
    var b = new Uint8Array(buf);
    var s = '';
    for (var i = 0; i < b.length; i++) s += (b[i] < 16 ? '0' : '') + b[i].toString(16);
    return s;
  }

  function sha256(buf) {
    return crypto.subtle.digest('SHA-256', buf).then(hex);
  }

  /* ---------------- gear 表 ---------------- */
  function loadGear(baseUrl, bits) {
    if (GEAR) return Promise.resolve(bits || 16);
    return fetch(baseUrl + 'gear.json').then(function (r) { return r.json(); })
      .then(function (j) {
        GEAR = new Uint32Array(256);
        GEAR_HI = new Uint32Array(256);
        j.gear.forEach(function (h, i) {
          /* 64 位拆成高低两个 32 位，JS 里做移位只能这样 */
          GEAR_HI[i] = parseInt(h.slice(0, 8), 16);
          GEAR[i] = parseInt(h.slice(8), 16);
        });
        return j.bits;
      });
  }

  /* ---------------- 分块（与 pack.py 完全一致） ---------------- */
  function chunksFixed(len, size) {
    var out = [];
    for (var o = 0; o < len; o += size) out.push({ o: o, l: Math.min(size, len - o) });
    return out;
  }

  function chunksCdc(buf, cdc) {
    var data = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
    var n = data.length;
    var out = [];
    if (!n) return out;
    var min = cdc.min, max = cdc.max, mask = (1 << cdc.bits) - 1;
    var hi = 0, lo = 0, start = 0;
    for (var i = 0; i < n; i++) {
      var g = data[i];
      /* h = (h << 1) + gear[g]，64 位用 (hi,lo) 模拟 */
      var nhi = ((hi << 1) | (lo >>> 31)) >>> 0;
      var nlo = (lo << 1) >>> 0;
      var lo2 = (nlo + GEAR[g]) >>> 0;
      var carry = lo2 < nlo ? 1 : 0;
      hi = (nhi + GEAR_HI[g] + carry) >>> 0;
      lo = lo2;
      var size = i - start + 1;
      if (size >= min && (lo & mask) === 0) {
        out.push({ o: start, l: size });
        start = i + 1; hi = 0; lo = 0;
      } else if (size >= max) {
        out.push({ o: start, l: size });
        start = i + 1; hi = 0; lo = 0;
      }
    }
    if (start < n) out.push({ o: start, l: n - start });
    return out;
  }

  function chunksOf(buf, manifest) {
    return manifest.chunkMode === 'cdc'
      ? chunksCdc(buf, manifest.cdc || { min: 16384, max: 262144, bits: 16 })
      : chunksFixed(buf.length, manifest.chunkSize || 65536);
  }

  /* ---------------- 索引本地已安装内容 ----------------
     files: {path: Uint8Array}
     opts.keepData=true 时把 chunk 原始字节也留下，拼装阶段要用
     返回 { have:{hash:{l,data?}}, sha:{path:hash}, bytes } */
  function localIndex(files, manifest, opts) {
    opts = opts || {};
    var have = Object.create(null);
    var sha = Object.create(null);
    var bytes = 0;
    var paths = Object.keys(files);
    var i = 0;

    function next() {
      if (i >= paths.length) {
        return Promise.resolve({ have: have, sha: sha, bytes: bytes, chunkData: have });
      }
      var path = paths[i++];
      var ab = files[path];
      var view = ab instanceof Uint8Array ? ab : new Uint8Array(ab);
      var parts = chunksOf(view, manifest);
      return Promise.all(parts.map(function (p) {
        var slice = view.slice(p.o, p.o + p.l);
        return sha256(slice).then(function (h) {
          if (!(h in have)) {
            have[h] = { l: p.l, data: opts.keepData ? slice : null };
            bytes += p.l;
          }
        });
      })).then(function () {
        return sha256(view).then(function (h) {
          sha[path] = h;
          if (opts.onProgress) opts.onProgress(i, paths.length);
          return next();
        });
      });
    }
    return next();
  }

  /* ---------------- 算差异 ----------------
     totalBytes / reuseBytes / needBytes 都按【去重后的唯一分块】统计，
     这样"省了多少"才和真实带宽一致（多个文件共用同一个块只算一次）。 */
  function plan(local, manifest) {
    var need = Object.create(null);
    var seen = Object.create(null);
    var needBytes = 0, totalBytes = 0, reuseBytes = 0;
    var want = Object.create(null);

    manifest.files.forEach(function (f) {
      want[f.path] = true;
      var untouched = local.sha[f.path] === f.sha256;
      f.chunks.forEach(function (c) {
        if (seen[c.h]) return;
        seen[c.h] = true;
        totalBytes += c.l;
        if (untouched || (c.h in local.have)) {
          reuseBytes += c.l;
        } else {
          need[c.h] = { h: c.h, l: c.l, files: [] };
          needBytes += c.l;
        }
      });
      /* 记下每个待下块被哪些文件用到，便于日志与宿主决定落盘顺序 */
      f.chunks.forEach(function (c) {
        if (need[c.h] && need[c.h].files.indexOf(f.path) < 0) {
          need[c.h].files.push(f.path);
        }
      });
    });

    var del = Object.keys(local.sha).filter(function (p) { return !want[p]; });
    return {
      need: Object.keys(need).map(function (h) { return need[h]; }),
      needBytes: needBytes,
      reuseBytes: reuseBytes,
      totalBytes: totalBytes,
      deleteFiles: del,
      changedFiles: manifest.files.filter(function (f) {
        return local.sha[f.path] !== f.sha256;
      }).map(function (f) { return f.path; }),
    };
  }

  /* ---------------- 执行 ----------------
     opts: { baseUrl, pattern, concurrency, retry, onProgress, shouldStop }
       baseUrl 指向 dist 根（末尾要有 /）
       pattern 用清单里的 chunkUrlPattern，如 "chunks/{h0}/{h}.bin"
     返回 { files:{path:Uint8Array}, deleted, stats } */
  function apply(local, manifest, pl, opts) {
    opts = opts || {};
    var base = opts.baseUrl || '';
    var pattern = opts.pattern || 'chunks/{h0}/{h}.bin';
    var conc = opts.concurrency || 6;
    var retry = opts.retry == null ? 3 : opts.retry;
    var store = Object.create(null);          // hash -> Uint8Array（新下的）
    var localChunks = local.have;             // 本地已有的
    var downloaded = 0, fetched = 0, failed = 0;
    var queue = pl.need.slice();
    var stopped = false;
    var errors = [];

    /* 注意 base 已经指向 dist 根，pattern 里自带 chunks/ —— 不要再拼一次 */
    function chunkUrl(h) {
      return base + pattern.replace('{h0}', h.slice(0, 2)).replace('{h}', h);
    }

    function fetchOne(item, attempt) {
      return fetch(chunkUrl(item.h), { cache: 'no-store' }).then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.arrayBuffer();
      }).then(function (ab) {
        if (ab.byteLength !== item.l) throw new Error('长度不符 ' + ab.byteLength + '≠' + item.l);
        var u8 = new Uint8Array(ab);
        return sha256(u8).then(function (h) {
          if (h !== item.h) throw new Error('分块 hash 不符');
          store[item.h] = u8;
          downloaded += item.l;
          fetched++;
          if (opts.onProgress) {
            opts.onProgress({
              done: fetched, total: pl.need.length,
              bytes: downloaded, totalBytes: pl.needBytes,
              percent: pl.need.length ? fetched / pl.need.length * 100 : 100,
            });
          }
        });
      }).catch(function (err) {
        if (attempt < retry && !stopped) {
          return new Promise(function (res) { setTimeout(res, 250 * (attempt + 1)); })
            .then(function () { return fetchOne(item, attempt + 1); });
        }
        failed++;
        errors.push({ chunk: item.h, error: String(err) });
        throw err;
      });
    }

    function worker() {
      if (stopped || (opts.shouldStop && opts.shouldStop())) { stopped = true; return Promise.resolve(); }
      var item = queue.shift();
      if (!item) return Promise.resolve();
      return fetchOne(item, 0).then(worker, function () { return worker(); });
    }

    var workers = [];
    for (var i = 0; i < Math.max(1, Math.min(conc, pl.need.length)); i++) workers.push(worker());

    return Promise.all(workers).then(function () {
      /* 拼装前先整体体检：把所有缺的块列出来，比一个一个报错好排查 */
      var missing = Object.create(null);
      manifest.files.forEach(function (f) {
        f.chunks.forEach(function (c) {
          if (!store[c.h] && !(localChunks[c.h] && localChunks[c.h].data)) {
            if (!missing[c.h]) {
              missing[c.h] = {
                h: c.h, l: c.l, files: [],
                inPlanNeed: pl.need.some(function (n) { return n.h === c.h; }),
                inLocalHave: c.h in localChunks,
                localHasData: !!(localChunks[c.h] && localChunks[c.h].data),
              };
            }
            missing[c.h].files.push(f.path);
          }
        });
      });
      var missList = Object.keys(missing).map(function (h) { return missing[h]; });
      if (missList.length) {
        var e = new Error('缺少 ' + missList.length + ' 个分块，首个: ' + missList[0].h);
        e.missing = missList.slice(0, 20);
        e.diag = {
          needCount: pl.need.length,
          fetched: fetched, failed: failed,
          storeSize: Object.keys(store).length,
          localHaveSize: Object.keys(localChunks).length,
          errors: errors.slice(0, 5),
        };
        throw e;
      }
      /* 拼装 */
      return Promise.all(manifest.files.map(function (f) {
        var buf = new Uint8Array(f.size);
        for (var k = 0; k < f.chunks.length; k++) {
          var c = f.chunks[k];
          var src = store[c.h] || (localChunks[c.h] && localChunks[c.h].data);
          if (!src) return Promise.reject(new Error('缺少分块 ' + c.h + '（' + f.path + '）'));
          buf.set(src, c.o);
        }
        return sha256(buf).then(function (h) {
          if (h !== f.sha256) throw new Error('整文件校验失败: ' + f.path);
          return { path: f.path, data: buf };
        });
      }));
    }).then(function (arr) {
      var files = Object.create(null);
      arr.forEach(function (x) { files[x.path] = x.data; });
      return {
        files: files,
        deleted: pl.deleteFiles.slice(),
        stopped: stopped,
        errors: errors,
        stats: {
          chunksTotal: pl.need.length,
          chunksFetched: fetched,
          chunksFailed: failed,
          bytesFetched: downloaded,
          bytesReused: pl.reuseBytes,
          bytesTotal: pl.totalBytes,
          savedPercent: pl.totalBytes ? (1 - downloaded / pl.totalBytes) * 100 : 0,
        },
      };
    });
  }

  /* ---------------- 一步到位（check + index + plan + apply） ---------------- */
  function update(localFiles, latestUrl, opts) {
    opts = opts || {};
    var distBase = latestUrl.replace(/[^/]*$/, '');   // .../dist/
    var state = {};
    return fetch(latestUrl).then(function (r) { return r.json(); })
      .then(function (j) {
        state.latest = j;
        /* 只有在 cdc 模式下才需要 gear 表 */
        return j.mode === 'cdc' ? loadGear(distBase) : null;
      })
      .then(function () {
        return fetch(distBase + state.latest.manifest);
      })
      .then(function (r) { return r.json(); })
      .then(function (m) {
        state.manifest = m;
        return localIndex(localFiles, m, {
          keepData: true, onProgress: opts.onIndex,
        });
      })
      .then(function (local) {
        state.local = local;
        state.plan = plan(local, state.manifest);
        if (opts.onPlan) opts.onPlan(state.plan, state.manifest);
        return apply(local, state.manifest, state.plan, {
          baseUrl: distBase,
          pattern: state.latest.chunkUrlPattern,
          concurrency: opts.concurrency,
          retry: opts.retry,
          onProgress: opts.onProgress,
          shouldStop: opts.shouldStop,
        });
      })
      .then(function (res) {
        res.manifest = state.manifest;
        res.plan = state.plan;
        res.latest = state.latest;
        return res;
      });
  }

  window.hoyoUpdater = {
    loadGear: loadGear,
    chunksOf: chunksOf,
    chunksFixed: chunksFixed,
    chunksCdc: chunksCdc,
    localIndex: localIndex,
    plan: plan,
    apply: apply,
    update: update,
    sha256: sha256,
    hex: hex,
  };
})();
