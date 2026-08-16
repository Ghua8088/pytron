import os
import subprocess
import xml.etree.ElementTree as ET


def show_toast(w, config):
    """
    Shows a modern Windows Toast notification using PowerShell and WinRT.
    Supports images, buttons, and custom layouts.
    """
    title = config.get("title", "Pytron")
    body = config.get("body", "")
    icon = config.get("icon")
    image = config.get("image")
    actions = config.get("actions", [])
    app_id = config.get("app_id", "Pytron.App")
    # Sanitize App ID (Windows prefers no spaces/special chars for unregistered IDs)
    safe_app_id = "".join(c if c.isalnum() or c in ".-" else "" for c in app_id)
    if not safe_app_id:
        safe_app_id = "Pytron.App"

    # 1. Build XML
    toast = ET.Element("toast", {"launch": "pytron://open"})
    visual = ET.SubElement(toast, "visual")
    binding = ET.SubElement(visual, "binding", {"template": "ToastGeneric"})

    ET.SubElement(binding, "text").text = title
    if body:
        ET.SubElement(binding, "text").text = body

    # App Icon Override
    if icon and os.path.exists(icon):
        icon_abs = os.path.abspath(icon)
        ET.SubElement(
            binding,
            "image",
            {
                "placement": "appLogoOverride",
                "src": icon_abs,
                "hint-crop": "circle" if config.get("circle_icon") else "none",
            },
        )

    # Hero Image
    if image and os.path.exists(image):
        hero_abs = os.path.abspath(image)
        ET.SubElement(binding, "image", {"placement": "hero", "src": hero_abs})

    # Inline Image
    inline_image = config.get("inline_image")
    if inline_image and os.path.exists(inline_image):
        inline_abs = os.path.abspath(inline_image)
        ET.SubElement(binding, "image", {"src": inline_abs})

    # Actions
    if actions:
        actions_elem = ET.SubElement(toast, "actions")
        for action in actions:
            label = action.get("label", "Action")
            args = action.get("action", "")

            action_props = {
                "content": label,
                "arguments": args,
            }

            if args.startswith("http") or args.startswith("pytron://"):
                action_props["activationType"] = "protocol"

            ET.SubElement(actions_elem, "action", action_props)

    xml_str = ET.tostring(toast, encoding="unicode")
    print(f"[Pytron] Debug Toast XML: {xml_str}")
    print(f"[Pytron] Debug Toast AppID: {app_id}")

    # 2. PowerShell Script
    # We use a heredoc for the XML to avoid escaping hell
    ps_script = f"""
$xmlString = @'
{xml_str}
'@

try {{
    # Load WinRT Assemblies
    [void][Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
    [void][Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime]

    $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
    $xml.LoadXml($xmlString)

    $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)

    # We'll try common IDs. PowerShell's own ID is very reliable for showing toasts from a script.
    $idsToTry = @(
        "{safe_app_id}",
        "{{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}}\\WindowsPowerShell\\v1.0\\powershell.exe",
        "Microsoft.Windows.Explorer"
    )

    $notifier = $null
    foreach ($id in $idsToTry) {{
        try {{
            $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($id)
            if ($notifier) {{ break }}
        }} catch {{ }}
    }}

    if ($notifier) {{
        $notifier.Show($toast)
    }} else {{
        throw "Failed to create ToastNotifier for any ID."
    }}
}} catch {{
    $_.Exception.Message | Out-String | Write-Error
}}
"""

    try:
        # Run hidden
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            check=False,
            creationflags=0x08000000,  # CREATE_NO_WINDOW
        )
        if res.stderr:
            print(f"[Pytron] Toast PowerShell Error: {res.stderr}")
    except Exception as e:
        print(f"[Pytron] Toast Subprocess Error: {e}")
