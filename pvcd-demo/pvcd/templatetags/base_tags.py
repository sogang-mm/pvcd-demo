import re
from collections import OrderedDict

from django import template
from django.template import loader
from django.urls import NoReverseMatch, reverse
from django.utils.encoding import iri_to_uri
from django.utils.html import escape, format_html, smart_urlquote
from django.utils.safestring import mark_safe

from rest_framework.compat import apply_markdown, pygments_highlight
from rest_framework.renderers import HTMLFormRenderer
from rest_framework.utils.urls import replace_query_param
from rest_framework.templatetags import rest_framework

register = template.Library()

# Regex for adding classes to html snippets
class_re = re.compile(r'(?<=class=["\'])(.*)(?=["\'])')


@register.simple_tag
def optional_login(request):
    """
    Include a login snippet if REST framework's login view is in the URLconf.
    """
    try:
        login_url = reverse('rest_framework:login')
    except NoReverseMatch:
        return ''

    snippet = "<li class='nav-item'><a class='nav-link' href='{href}?next={next}'>Log in</a></li>"
    snippet = format_html(snippet, href=login_url, next=escape(request.path))

    return mark_safe(snippet)


@register.simple_tag
def optional_logout(request, user):
    """
    Include a logout snippet if REST framework's logout view is in the URLconf.
    """
    try:
        logout_url = reverse('rest_framework:logout')
    except NoReverseMatch:
        snippet = format_html('<li class="navbar-text">{user}</li>', user=escape(user))
        return mark_safe(snippet)

    snippet = """<li class="nav-item dropdown">
        <a href="#" class="nav-link" data-toggle="dropdown">
            {user}
            <b class="caret dropdown-toggle"></b>
        </a>
        <ul class="dropdown-menu">
            <a class="dropdown-item" href='{href}?next={next}'>Log out</a>
        </ul>
    </li>"""
    snippet = format_html(snippet, user=escape(user), href=logout_url, next=escape(request.path))

    return mark_safe(snippet)


@register.simple_tag
def render_form(serializer, template_pack=None):
    return rest_framework.render_form(serializer, template_pack)


@register.simple_tag
def render_field(field, style):
    return rest_framework.render_field(field, style)

@register.filter
def add_class(value, css_class):
    return rest_framework.add_class(value, css_class)