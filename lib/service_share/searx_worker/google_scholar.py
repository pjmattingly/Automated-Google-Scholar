# SPDX-License-Identifier: AGPL-3.0-or-later
"""Google (Scholar)

For detailed description of the *REST-full* API see: `Query Parameter
Definitions`_.

.. _Query Parameter Definitions:
   https://developers.google.com/custom-search/docs/xml_results#WebSearch_Query_Parameter_Definitions
"""

# pylint: disable=invalid-name, missing-function-docstring

from urllib.parse import urlencode
from datetime import datetime
from lxml import html
from searx import logger

from searx.utils import (
    eval_xpath,
    eval_xpath_list,
    extract_text,
)

from searx.engines.google import (
    get_lang_info,
    time_range_dict,
    detect_google_sorry,
)

# pylint: disable=unused-import
from searx.engines.google import (
    supported_languages_url,
    _fetch_supported_languages,
)
# pylint: enable=unused-import

# about
about = {
    "website": 'https://scholar.google.com',
    "wikidata_id": 'Q494817',
    "official_api_documentation": 'https://developers.google.com/custom-search',
    "use_official_api": False,
    "require_api_key": False,
    "results": 'HTML',
}

# engine dependent config
categories = ['science']
paging = True
language_support = True
use_locale_domain = True
time_range_support = True
safesearch = False

logger = logger.getChild('google scholar')

def time_range_url(params):
    """Returns a URL query component for a google-Scholar time range based on
    ``params['time_range']``.  Google-Scholar does only support ranges in years.
    To have any effect, all the Searx ranges (*day*, *week*, *month*, *year*)
    are mapped to *year*.  If no range is set, an empty string is returned.
    Example::

        &as_ylo=2019
    """
    # as_ylo=2016&as_yhi=2019
    ret_val = ''
    if params['time_range'] in time_range_dict:
        ret_val= urlencode({'as_ylo': datetime.now().year -1 })
    return '&' + ret_val

def request(query, params):
    """Google-Scholar search request"""

    offset = (params['pageno'] - 1) * 10
    lang_info = get_lang_info(
        # pylint: disable=undefined-variable


        # params, {}, language_aliases

        params, supported_languages, language_aliases
    )
    # subdomain is: scholar.google.xy
    lang_info['subdomain'] = lang_info['subdomain'].replace("www.", "scholar.")

    '''
    Note
    This is a modified version of the google scholar engine
    available from the searx project
        see:
        https://github.com/searx/searx/blob/master/searx/engines/google_scholar.py
    This engine is intended to work with a custom
    REST API implementation
    One notable feature is that all input queries to
    this engine (the "query" varaible) are assumed to be
    JSON
    The various parameters for "query_url" are then extracted
    from this.
    The reason for this was to implement some of Google Scholar's
    more advanced features
        e.g. searching in a specific time-frame for a set of papers
        see:
        https://serpapi.com/google-scholar-api
    A backup of the original engine can be found at this path
        /usr/local/searx/searx/engines/google_scholar.py.bak
    '''
    import json
    json_query_payload = json.loads( query )
    d_query_url = {
        'hl': lang_info['hl'],
        'lr': lang_info['lr'],
        'ie': "utf8",
        'oe':  "utf8",
        'start' : offset,
    }

    #add the defined keys from the query to the query_url
    #'q':  str(json_query_payload['q']),
    #'as_ylo': str(json_query_payload['as_ylo']),
    #'as_yhi': str(json_query_payload['as_yhi']),
    for k in json_query_payload:
        if k not in d_query_url:
            d_query_url[k] = str(json_query_payload[k])

    query_url = 'https://'+ lang_info['subdomain'] + '/scholar' + "?" + urlencode(d_query_url)

    #NOTE
    #disabled time_range support here
    #to avoid interfering with other similar
    #parameter set above
    #query_url += time_range_url(params)

    logger.debug("query_url --> %s", query_url)
    params['url'] = query_url

    logger.debug("HTTP header Accept-Language --> %s", lang_info['Accept-Language'])
    params['headers']['Accept-Language'] = lang_info['Accept-Language']
    params['headers']['Accept'] = (
        'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    )

    #params['google_subdomain'] = subdomain
    return params

def response(resp):
    """Get response from google's search request"""
    results = []

    detect_google_sorry(resp)

    # which subdomain ?
    # subdomain = resp.search_params.get('google_subdomain')

    # convert the text to dom
    dom = html.fromstring(resp.text)

    # parse results
    for result in eval_xpath_list(dom, '//div[@class="gs_ri"]'):

        title = extract_text(eval_xpath(result, './h3[1]//a'))

        if not title:
            # this is a [ZITATION] block
            continue

        url = eval_xpath(result, './h3[1]//a/@href')[0]
        content = extract_text(eval_xpath(result, './div[@class="gs_rs"]')) or ''

        pub_info = extract_text(eval_xpath(result, './div[@class="gs_a"]'))
        if pub_info:
            content += "[%s]" % pub_info

        pub_type = extract_text(eval_xpath(result, './/span[@class="gs_ct1"]'))
        if pub_type:
            title = title + " " + pub_type

        results.append({
            'url':      url,
            'title':    title,
            'content':  content,
        })

    # parse suggestion
    for suggestion in eval_xpath(dom, '//div[contains(@class, "gs_qsuggest_wrap")]//li//a'):
        # append suggestion
        results.append({'suggestion': extract_text(suggestion)})

    for correction in eval_xpath(dom, '//div[@class="gs_r gs_pda"]/a'):
        results.append({'correction': extract_text(correction)})

    return results
