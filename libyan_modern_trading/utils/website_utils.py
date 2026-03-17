import frappe

def get_website_context(context):
    lmt_settings = frappe.db.get_value(
        'LMT Mobile Menu Item',
        {'route': 'webpage_colors_and_tilte'},
        ['background_color', 'grid_background_color'],
        as_dict=True
    )

    if lmt_settings:
        context.setdefault('head_html', '')
        context['head_html'] += f"""
<style id="lmt-global-sync">
    .navbar, .topbar, .page-head, .web-page-header, .drawer-header {{
        background-color: {lmt_settings.background_color} !important;
    }}
    body, .page-container, .web-page-content, .content, .appshell, .page-body {{
        background-color: {lmt_settings.grid_background_color} !important;
    }}
    .web-page, .container {{ background-color: transparent !important; }}
</style>
"""

