(function () {
  'use strict';

  var API_BASE = (window.YT_SAVER_API_BASE || '').replace(/\/$/, '');

  var YT_REGEX = /^(https?:\/\/)?(www\.|m\.)?(youtube\.com\/(watch\?v=|shorts\/)|youtu\.be\/)([\w-]{11})/;

  var $url = document.getElementById('url');
  var $urlGroup = document.getElementById('url-group');
  var $urlError = document.getElementById('url-error');
  var $quality = document.getElementById('quality');
  var $bitrate = document.getElementById('bitrate');
  var $mp4 = document.getElementById('btn-mp4');
  var $mp3 = document.getElementById('btn-mp3');
  var $alert = document.getElementById('alert');
  var $progressWrap = document.getElementById('progress-wrap');
  var $progressBar = document.getElementById('progress-bar');
  var $progressLabel = document.getElementById('progress-label');
  var $result = document.getElementById('result');
  var $resultThumb = document.getElementById('result-thumb');
  var $resultTitle = document.getElementById('result-title');
  var $resultChannel = document.getElementById('result-channel');
  var $resultDuration = document.getElementById('result-duration');
  var $resultDownload = document.getElementById('result-download');
  var $resultReset = document.getElementById('result-reset');
  var $year = document.getElementById('year');

  $year.textContent = String(new Date().getFullYear());

  function track(name, params) {
    if (typeof window.gtag === 'function') {
      try { window.gtag('event', name, params || {}); } catch (e) {}
    }
  }

  function isValid(url) { return YT_REGEX.test((url || '').trim()); }

  function setButtonsEnabled(enabled) {
    $mp4.disabled = !enabled;
    $mp3.disabled = !enabled;
  }

  function showError(message) {
    $alert.className = 'alert alert-error';
    $alert.textContent = message;
    $alert.style.display = 'block';
  }

  function clearError() {
    $alert.style.display = 'none';
    $alert.textContent = '';
    $alert.className = 'alert';
  }

  function showProgress(percent, label) {
    $progressWrap.style.display = 'block';
    $progressBar.style.width = (percent != null ? percent : 0) + '%';
    if (label) $progressLabel.textContent = label;
  }

  function hideProgress() {
    $progressWrap.style.display = 'none';
    $progressBar.style.width = '0%';
  }

  function fmtDuration(seconds) {
    seconds = Number(seconds || 0);
    var m = Math.floor(seconds / 60);
    var s = Math.floor(seconds % 60);
    return m + ':' + (s < 10 ? '0' + s : s);
  }

  function showResult(info, downloadUrl) {
    $resultThumb.src = info.thumbnail || '';
    $resultThumb.alt = info.title || '';
    $resultTitle.textContent = info.title || '';
    $resultChannel.textContent = info.channel || '';
    $resultDuration.textContent = fmtDuration(info.duration);
    $resultDownload.href = downloadUrl;
    $result.style.display = 'block';
  }

  function reset() {
    hideProgress();
    clearError();
    $result.style.display = 'none';
    setButtonsEnabled(isValid($url.value));
  }

  function api(path, options) {
    return fetch(API_BASE + path, options).then(function (res) {
      if (!res.ok) {
        return res.json().catch(function () { return {}; }).then(function (body) {
          var msg = (body && body.detail) || ('Request failed (' + res.status + ')');
          throw new Error(msg);
        });
      }
      return res.json();
    });
  }

  function pollJob(jobId) {
    return new Promise(function (resolve, reject) {
      var startedAt = Date.now();
      var TIMEOUT_MS = 600000;
      function tick() {
        api('/api/jobs/' + encodeURIComponent(jobId)).then(function (job) {
          if (job.status === 'ready') return resolve(job);
          if (job.status === 'error') return reject(new Error(job.error || 'Conversion failed'));
          showProgress(job.progress != null ? job.progress : null, job.status === 'processing' ? 'Converting…' : 'Queued…');
          if (Date.now() - startedAt > TIMEOUT_MS) return reject(new Error('Timed out waiting for conversion'));
          setTimeout(tick, 1500);
        }).catch(reject);
      }
      tick();
    });
  }

  function submit(format) {
    var url = $url.value.trim();
    if (!isValid(url)) return;

    var body = { url: url, format: format };
    if (format === 'mp4') {
      body.quality = $quality.value;
      track('download_click_mp4', { quality: body.quality });
    } else {
      body.quality = $bitrate.value;
      track('download_click_mp3', { bitrate: body.quality });
    }

    clearError();
    $result.style.display = 'none';
    setButtonsEnabled(false);
    showProgress(0, 'Starting…');

    api('/api/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
      .then(function (resp) { return pollJob(resp.jobId); })
      .then(function (job) {
        hideProgress();
        var downloadUrl = API_BASE + job.downloadUrl;
        showResult(job.info || {}, downloadUrl);
        track('download_success', {
          format: format,
          quality: body.quality,
          duration_s: (job.info && job.info.duration) || 0
        });
      })
      .catch(function (err) {
        hideProgress();
        showError(err.message || 'Something went wrong');
        track('download_error', { reason: err.message || 'unknown' });
      })
      .then(function () {
        setButtonsEnabled(isValid($url.value));
      });
  }

  $url.addEventListener('input', function () {
    var ok = isValid($url.value);
    $urlGroup.className = 'control-group' + (ok || !$url.value ? '' : ' error');
    $urlError.style.display = (!ok && $url.value) ? 'inline' : 'none';
    setButtonsEnabled(ok);
  });

  $mp4.addEventListener('click', function (e) {
    e.preventDefault();
    $quality.style.display = '';
    $bitrate.style.display = 'none';
    submit('mp4');
  });

  $mp3.addEventListener('click', function (e) {
    e.preventDefault();
    submit('mp3');
  });

  $resultReset.addEventListener('click', function (e) {
    e.preventDefault();
    $url.value = '';
    $url.dispatchEvent(new Event('input'));
    reset();
  });

  // Toggle quality vs bitrate selector based on intent — show bitrate when user hovers MP3
  $mp3.addEventListener('mouseenter', function () {
    $quality.style.display = 'none';
    $bitrate.style.display = '';
  });
  $mp4.addEventListener('mouseenter', function () {
    $quality.style.display = '';
    $bitrate.style.display = 'none';
  });
})();
