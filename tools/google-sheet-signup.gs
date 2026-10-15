/**
 * Augmenting Decision: launch sign-ups, stored in a private Google Sheet.
 *
 * Setup (see README, "Sign-up form"):
 *   1. In the Google Sheet: Extensions > Apps Script, replace everything with this file.
 *   2. Deploy > New deployment > Web app.
 *      Execute as: Me. Who has access: Anyone. Then copy the Web app URL.
 *   3. Put that URL in assets/js/main.js (SIGNUP_ENDPOINT).
 *
 * Each sign-up adds one row: date, email, language, page. Duplicates are ignored.
 */
var SHEET_NAME = 'Sign-ups';

function doPost(e) {
  var p = (e && e.parameter) || {};
  // The hidden "website" field is only ever filled in by spam bots.
  if (p.website) return reply_('ok');

  var email = String(p.email || '').trim().toLowerCase();
  if (email.length > 254 || !/^[a-z0-9][a-z0-9._%+'-]*@[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}$/.test(email)) {
    return reply_('invalid');
  }

  var lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    var sheet = getSheet_();
    var last = sheet.getLastRow();
    if (last > 1) {
      var existing = sheet.getRange(2, 2, last - 1, 1).getValues().map(function (r) { return r[0]; });
      if (existing.indexOf(email) !== -1) return reply_('ok');
    }
    sheet.appendRow([new Date(), email, clean_(p.lang, 5), clean_(p.page, 100)]);
  } finally {
    lock.releaseLock();
  }
  return reply_('ok');
}

function doGet() {
  return reply_('The Augmenting Decision sign-up form is connected.');
}

function getSheet_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    sheet.appendRow(['Date', 'Email', 'Language', 'Page']);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

// Short plain text only, so nothing a visitor sends can act as a spreadsheet formula.
function clean_(value, max) {
  return String(value || '').replace(/[^a-zA-Z0-9\/._-]/g, '').slice(0, max);
}

function reply_(text) {
  return ContentService.createTextOutput(text).setMimeType(ContentService.MimeType.TEXT);
}
