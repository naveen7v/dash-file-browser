import base64
import datetime
import os
from pathlib import Path
from urllib.parse import quote as urlquote

from loguru import logger
import flask
import dash_bootstrap_components as dbc
import pandas as pd
from dash import ALL, Dash, Input, Output, State, callback_context, dcc, html
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from icons import icons


def icon_file(extension, width=24, height=24):
    """Retrun an html.img of the svg icon for a given extension."""
    filetype = icons.get(extension)
    file_name = f'file_type_{filetype}.svg' if filetype is not None else 'default_file.svg'
    html_tag = html.Img(src=app.get_asset_url(f'icons/{file_name}'),
                        width=width, height=height)
    return html_tag


def nowtimestamp(timestamp, fmt='%b %d, %Y %H:%M'):
    return datetime.datetime.fromtimestamp(timestamp).strftime(fmt)


def file_info(path):
    """Get file info for a given path.
    Uncomment the attributes that you want to display.

    Parameters:
    -----------
    path : pathlib.Path object
    """
    file_stat = path.stat()
    return {
        'extension': path.suffix if not path.name.startswith('.') else path.name,
        'filename': path.name,
        # 'fullpath': str(path.absolute()),
        'size': format(file_stat.st_size, ','),
        'created': nowtimestamp(file_stat.st_ctime),
        'modified': nowtimestamp(file_stat.st_mtime),
        # 'accessed': nowtimestamp(file_stat.st_atime),
        # 'is_dir': str(path.is_dir()),
        # 'is_file': str(path.is_file()),
    }


app = Dash(
    __name__,
    title='Dash File Browser',
    assets_folder='assets',
    external_stylesheets=[dbc.themes.FLATLY]
)

server = app.server


@server.route("/download/<path:path>")
def download(path):
    """Serve a file from the upload directory."""

    #return send_from_directory(UPLOAD_DIRECTORY, path, as_attachment=True)


@server.route('/divinfo', methods=['POST', 'GET'])
def get_divinfo():
   divinfo = flask.request.get_json()
   logger.warning(divinfo)
   return flask.jsonify({"result":'ok'})


app.layout = html.Div([
    html.Link(
        rel="stylesheet",
        href="https://cdnjs.cloudflare.com/ajax/libs/github-fork-ribbon-css/0.2.3/gh-fork-ribbon.min.css"
    ),
    
    dbc.Row([
        dbc.Col(lg=1, sm=1, md=1),
        
        dbc.Col([
            dcc.Store(id='stored_cwd', data=os.getcwd()),
            
            html.H5(html.B(html.A("⬆️ Parent directory", href='#',
                                  id='parent_dir'))),
            dbc.Row([
                dbc.Col([
                    html.H5(["Current Path: ", html.Code(os.getcwd(), id='cwd')])
                ], width=8),
                
                dbc.Col([
                    dcc.Upload(
                        id='file-up', children="Click to Upload File(s)", multiple=True,
                        style={
                            'width': '100%', 'height': '60px',
                            'lineHeight': '60px', 'borderWidth': '1px',
                            'borderStyle': 'dashed',
                            'borderRadius': '5px', 'textAlign': 'center',
                            'margin': '10px'
                        }
                    )
                ], width=2),
                
                dbc.Col([
                    dbc.Button("Downlaod selected files", id="dwn-btn"), 
                    dcc.Download(id="downloader")
                ])
                
            ]),
            html.Br(),
            
            html.Div(id='cwd_files',
                     style={'height': 600, 'overflow': 'scroll'}),
        ], lg=10, sm=11, md=10)
    ])
] + [html.Br() for _ in range(15)])



def file_upload_to_cur_dir(file_names, file_contents, cur_dir):
    if file_names is not None and file_contents is not None:
        for name, fdata in zip(file_names, file_contents):
            data = fdata.encode("utf8").split(b";base64,")[1]
            with open(os.path.join(cur_dir, name), "wb") as fp:
                fp.write(base64.decodebytes(data))


@app.callback(
    Output('cwd', 'children'),
    Input('stored_cwd', 'data'), Input('parent_dir', 'n_clicks'), Input('cwd', 'children'),
    prevent_initial_call=True
)
def get_parent_directory(stored_cwd, n_clicks, currentdir):
    triggered_id = callback_context.triggered_id
    if triggered_id == 'stored_cwd':
        return stored_cwd
    parent = Path(currentdir).parent.as_posix()
    return parent


@app.callback(
    Output('cwd_files', 'children'),
    Input('cwd', 'children'), Input('file-up', 'filename'), Input('file-up', 'contents'),
    State('stored_cwd', 'data')
)
def list_cwd_files(cwd, file_name, file_contents, cur_dir):
    triggered_id = callback_context.triggered_id
    if triggered_id == 'file-up':
        file_upload_to_cur_dir(file_name, file_contents, cur_dir)

    path = Path(cwd)
    all_file_details = []
    if path.is_dir():
        files = sorted(os.listdir(path), key=str.lower)
        for i, file in enumerate(files):
            filepath = Path(file)
            full_path=os.path.join(cwd, filepath.as_posix())
            is_dir = Path(full_path).is_dir()
            
            details = file_info(Path(full_path))
            
            if is_dir:
                link = html.A([
                    html.Span(
                    file, id={'type': 'listed_file', 'index': i},
                    title=full_path,
                    style={'fontWeight': 'bold', 'fontSize': 18} if is_dir else {}
                )], href="#")
                details['filename'] = link
                details['extension'] = html.Img(
                    src=app.get_asset_url('icons/default_folder.svg'),
                    width=25, height=25)
            else:
                link = html.A([
                    html.Span(
                    file, id={'type': 'listed_file', 'index': i},
                    title=full_path,
                    style={'fontWeight': 'bold', 'fontSize': 18} if is_dir else {}
                )], href="/download/{}".format(urlquote(file)))
                details['filename'] = link
                details['extension'] = icon_file(details['extension'][1:])
            
            all_file_details.append(details)

    df = pd.DataFrame(all_file_details).rename(columns={"extension": ''})
    return html.Div(
        dbc.Table.from_dataframe(
            df, striped=False, bordered=False, hover=True, size='sm'
        )
    )


@app.callback(
    Output('stored_cwd', 'data'),
    Input({'type': 'listed_file', 'index': ALL}, 'n_clicks'),
    State({'type': 'listed_file', 'index': ALL}, 'title')
)
def store_clicked_file(n_clicks, title):
    if not n_clicks or set(n_clicks) == {None}:
        raise PreventUpdate
    ctx = callback_context
    index = ctx.triggered_id['index']
    return title[index]


if __name__ == '__main__':
    app.run_server(debug=True)
