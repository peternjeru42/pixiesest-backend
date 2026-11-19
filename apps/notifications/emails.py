from html import escape
from urllib.parse import urlparse

from django.conf import settings
from django.core.mail import EmailMultiAlternatives


BRAND_GREEN = "#087A63"
INK = "#171A1A"
MUTED = "#68706D"
PANEL = "#F3F6F4"


def _safe_url(value):
    value = (value or "").strip()
    parsed = urlparse(value)
    return value if parsed.scheme in {"http", "https"} and parsed.netloc else ""


def _paragraphs_html(paragraphs):
    return "".join(
        f'<p style="margin:0 0 14px;color:{MUTED};font-size:16px;line-height:1.65;">{escape(str(paragraph))}</p>'
        for paragraph in paragraphs
        if paragraph
    )


def _details_html(details):
    if not details:
        return ""
    rows = "".join(
        (
            '<tr>'
            f'<td style="padding:9px 0;color:{MUTED};font-size:13px;line-height:1.4;vertical-align:top;">{escape(str(label))}</td>'
            f'<td style="padding:9px 0 9px 20px;color:{INK};font-size:13px;font-weight:600;line-height:1.4;text-align:right;vertical-align:top;">{escape(str(value))}</td>'
            '</tr>'
        )
        for label, value in details
        if value not in {None, ""}
    )
    if not rows:
        return ""
    return (
        f'<div style="margin:24px 0;padding:10px 20px;background:{PANEL};border:1px solid #E4EAE7;border-radius:14px;">'
        f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">{rows}</table>'
        '</div>'
    )


def _metrics_html(metrics):
    if not metrics:
        return ""
    cells = "".join(
        (
            '<td style="padding:0 6px 0 0;vertical-align:top;">'
            f'<div style="padding:18px 14px;background:{PANEL};border:1px solid #E4EAE7;border-radius:14px;text-align:center;">'
            f'<div style="color:{INK};font-size:26px;font-weight:700;line-height:1.1;letter-spacing:-0.03em;">{escape(str(value))}</div>'
            f'<div style="margin-top:6px;color:{MUTED};font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;">{escape(str(label))}</div>'
            '</div></td>'
        )
        for label, value in metrics
    )
    return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:24px 0;"><tr>{cells}</tr></table>'


def render_branded_email(*, preheader, eyebrow, heading, paragraphs, cta_label="", cta_url="", details=None, metrics=None, note=""):
    safe_cta_url = _safe_url(cta_url)
    button = ""
    if cta_label and safe_cta_url:
        button = (
            '<table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:28px 0 8px;"><tr><td>'
            f'<a href="{escape(safe_cta_url, quote=True)}" style="display:inline-block;padding:14px 22px;background:{INK};border-radius:999px;color:#FFFFFF;font-size:14px;font-weight:700;line-height:1;text-decoration:none;">{escape(cta_label)}</a>'
            '</td></tr></table>'
        )
    note_html = ""
    if note:
        note_html = f'<p style="margin:24px 0 0;color:#88908D;font-size:12px;line-height:1.6;">{escape(note)}</p>'

    return f'''<!doctype html>
<html lang="en">
  <head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(heading)}</title></head>
  <body style="margin:0;padding:0;background:#EEF2F0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;color:{INK};">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">{escape(preheader)}</div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#EEF2F0;">
      <tr><td align="center" style="padding:34px 14px;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:620px;">
          <tr><td style="padding:0 6px 20px;">
            <table role="presentation" cellspacing="0" cellpadding="0" border="0"><tr>
              <td style="width:34px;height:34px;border-radius:11px;background:{BRAND_GREEN};color:#FFFFFF;font-size:16px;font-weight:800;text-align:center;vertical-align:middle;">D</td>
              <td style="padding-left:11px;color:{INK};font-size:15px;font-weight:800;letter-spacing:0.12em;">DROPTOP</td>
            </tr></table>
          </td></tr>
          <tr><td style="padding:42px 40px;background:#FFFFFF;border:1px solid #E1E7E4;border-radius:22px;box-shadow:0 12px 40px rgba(30,45,39,0.06);">
            <div style="margin-bottom:12px;color:{BRAND_GREEN};font-size:11px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;">{escape(eyebrow)}</div>
            <h1 style="margin:0 0 18px;color:{INK};font-size:34px;font-weight:750;line-height:1.12;letter-spacing:-0.035em;">{escape(heading)}</h1>
            {_paragraphs_html(paragraphs)}
            {_metrics_html(metrics or [])}
            {_details_html(details or [])}
            {button}
            {note_html}
          </td></tr>
          <tr><td style="padding:20px 8px 0;color:#7B8380;font-size:11px;line-height:1.6;text-align:center;">
            Sent by Droptop · Beautiful client galleries, without the clutter.<br>
            This is a transactional email related to your Droptop account or gallery activity.
          </td></tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>'''


def send_branded_email(*, recipient, subject, preheader, eyebrow, heading, paragraphs, cta_label="", cta_url="", details=None, metrics=None, note="", reply_to=None):
    details = details or []
    metrics = metrics or []
    text_lines = [heading, "", *[str(paragraph) for paragraph in paragraphs if paragraph]]
    if metrics:
        text_lines.extend(["", *[f"{label}: {value}" for label, value in metrics]])
    if details:
        text_lines.extend(["", *[f"{label}: {value}" for label, value in details if value not in {None, ""}]])
    if cta_label and _safe_url(cta_url):
        text_lines.extend(["", f"{cta_label}: {cta_url}"])
    if note:
        text_lines.extend(["", note])

    message = EmailMultiAlternatives(
        subject=subject,
        body="\n".join(text_lines),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
        reply_to=[reply_to] if reply_to else None,
    )
    message.attach_alternative(
        render_branded_email(
            preheader=preheader,
            eyebrow=eyebrow,
            heading=heading,
            paragraphs=paragraphs,
            cta_label=cta_label,
            cta_url=cta_url,
            details=details,
            metrics=metrics,
            note=note,
        ),
        "text/html",
    )
    return message.send(fail_silently=False)
