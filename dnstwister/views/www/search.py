"""Search/report page."""
import json

import flask

from dnstwister import app
import dnstwister.tools as tools


def html_render(domain):
    """Render and return the html report."""
    reports = dict([tools.analyse(domain)])

    return flask.render_template(
        'www/report.html',
        reports=reports,
        atoms=dict([(domain, tools.encode_domain(domain))]),
        exports={'json': 'json', 'csv': 'csv'},
        domain_encoded=tools.encode_domain(domain),
    )


def json_render(domain):
    """Render and return the json-formatted report.

    The hand-assembly is due to the streaming of the response.
    """
    reports = dict([tools.analyse(domain)])

    json_filename = 'dnstwister_report_{}.json'.format(domain.encode('idna'))

    def generate():
        """Streaming download generator."""
        indent_size = 4
        indent = ' ' * indent_size

        yield '{\n'

        # TODO: We only have one domain now, simplify this.
        for (dom, rept) in reports.items():

            yield indent + '"' + dom.encode('idna') + '": {\n'
            yield indent * 2 + '"fuzzy_domains": [\n'

            fuzzy_domains = rept['fuzzy_domains']
            for (j, entry) in enumerate(fuzzy_domains):

                ip_addr, error = tools.resolve(entry['domain-name'])
                data = {
                    'domain-name': entry['domain-name'].encode('idna'),
                    'fuzzer': entry['fuzzer'],
                    'hex': entry['hex'],
                    'resolution': {
                        'error': error,
                        'ip': ip_addr,
                    },
                }

                json_str = json.dumps(
                    data,
                    sort_keys=True,
                    indent=indent_size,
                    separators=(',', ': ')
                )
                yield '\n'.join([indent * 3 + line
                                 for line
                                 in json_str.split('\n')])
                if j < len(fuzzy_domains) - 1:
                    yield ','
                yield '\n'

            yield indent * 2 + ']\n'
            yield indent + '}'
            yield '\n'

        yield '}\n'

    return flask.Response(
        generate(),
        headers={
            'Content-Disposition': 'attachment; filename=' + json_filename
        },
        content_type='application/json'
    )


def csv_render(domain):
    """Render and return the csv-formatted report."""
    headers = ('Domain', 'Type', 'Tweak', 'IP', 'Error')
    reports = dict([tools.analyse(domain)])

    csv_filename = 'dnstwister_report_{}.csv'.format(domain.encode('idna'))

    def generate():
        """Streaming download generator."""
        yield ','.join(headers) + '\n'
        for (domain, rept) in reports.items():
            for entry in rept['fuzzy_domains']:
                ip_addr, error = tools.resolve(entry['domain-name'])

                row = (
                    domain.encode('idna'),
                    entry['fuzzer'],
                    entry['domain-name'].encode('idna'),
                    str(ip_addr),
                    str(error),
                )
                # comma not possible in any of the row values.
                yield u','.join(row) + '\n'

    return flask.Response(
        generate(),
        headers={
            'Content-Disposition': 'attachment; filename=' + csv_filename
        },
        mimetype='text/csv',
    )


@app.route('/search', methods=['POST'])
def search_post():
    """Handle form submit."""
    try:
        post_data = flask.request.form['domains']
    except KeyError:
        app.logger.info(
            'Missing "domains" key from POST: {}'.format(flask.request.form)
        )
        return flask.redirect('/error/2')

    if post_data is None or post_data.strip() == '':
        app.logger.info(
            'No data in "domains" key in POST'
        )
        return flask.redirect('/error/2')

    search_parameter = tools.encode_domain(post_data)

    if search_parameter is None:
        app.logger.info(
            'Invalid POST Unicode data:{}'.format(repr(post_data))
        )
        return flask.redirect('/error/0')

    return flask.redirect('/search/{}'.format(search_parameter))


def handle_invalid_domain(search_term_as_hex):
    """Called when no valid domain found in GET param, creates a suggestion
    to return to the user.
    """
    decoded_search = None
    try:
        decoded_search = tools.decode_domain(search_term_as_hex)
    except:
        pass

    if decoded_search is not None:
        suggestion = tools.suggest_domain(decoded_search)
        if suggestion is not None:
            app.logger.info(
                'Not a valid domain in GET: {}, suggesting: {}'.format(
                    search_term_as_hex, suggestion
                )
            )
            encoded_suggestion = tools.encode_domain(suggestion)
            return flask.redirect(
                '/error/0?suggestion={}'.format(encoded_suggestion)
            )

    app.logger.info(
        'Not a valid domain in GET: {}'.format(search_term_as_hex)
    )
    return flask.redirect('/error/0')


@app.route('/search/<search_domain>')
@app.route('/search/<search_domain>/<fmt>')
def search(search_domain, fmt=None):
    """Handle redirect from form submit."""
    domain = tools.parse_post_data(search_domain)

    if domain is None:
        return handle_invalid_domain(search_domain)

    if fmt is None:
        return html_render(domain)
    elif fmt == 'json':
        return json_render(domain)
    elif fmt == 'csv':
        return csv_render(domain)
    else:
        flask.abort(400, 'Unknown export format: {}'.format(fmt))
