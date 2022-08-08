
from __future__ import print_function
from distutils.sysconfig import PREFIX
from flask import Blueprint, jsonify, request as req
import requests
from bs4 import BeautifulSoup
from graphdb import rdf4j
from graphdb.mime_types import RDFTypes
import urllib
from urllib.parse import urlparse
from duckduckgo_search import ddg
import pandas as pd
import io

blueprint = Blueprint('api', __name__)
  
repository_id = 'TrabalhoFinal'
conf = rdf4j.Configuration()
conf.host = "http://localhost:7200/"
api_client = rdf4j.api_client.ApiClient(configuration=conf)
api_client.set_default_header("Content-Type", RDFTypes.TURTLE)

api = rdf4j.api.repositories_api.RepositoriesApi(api_client)

PREFIXES = {
  'ex': 'http://example.org/',
  'foaf': 'http://xmlns.com/foaf/0.1/',
  'gn': 'http://www.geonames.org/ontology#',
  'owl': 'http://www.w3.org/2002/07/owl#',
  'path': 'http://www.ontotext.com/path#',
  'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
  'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
  'wgs': 'http://www.w3.org/2003/01/geo/wgs84_pos#',
  'xsd': 'http://www.w3.org/2001/XMLSchema#'
}

@blueprint.route('/validate', methods=['POST'])
def validate():
  params = req.get_json()
  target_url = params.get('url')
  target_url = urlparse(target_url)

  target_metadata = extract_metadata(f'{target_url.scheme}://{target_url.netloc}')

  target_id = f'target_{target_url.netloc}'
  rdf = create_rdf(target_id, target_metadata)

  graphdb_stmt = f'''
@prefix ex:<http://example.org/>  .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
  {rdf}'''

  # Prepare search
  terms = []
  if('title' in target_metadata):
    terms.append(target_metadata['title'])
  if('keywords' in target_metadata):
    terms.append(target_metadata['keywords'])

  search_result = search_duckduckgo(terms, max_results=3)

  searched_domains = []
  for url in search_result:
    url = urlparse(url)
    domain = url.netloc
    if(domain in searched_domains):
      continue
    searched_domains.append(domain)
    meta = extract_metadata(f'{url.scheme}://{domain}')
    normalized_url = normalize_url(f'{url.scheme}://{domain}')
    rdf = create_rdf(normalized_url, meta)
    graphdb_stmt += rdf
  
  save_rdf(graphdb_stmt)

  result = check_for_isomorphic_graphs(f'ex:{target_id}')

  return jsonify({'url': target_url.netloc, 'rdf': graphdb_stmt, 'metadata': target_metadata, 'search_result': search_result, 'result': result})


def extract_metadata(url):
  print('Extracting metadata from website: ', url)
  response = requests.get(url)
  response.raise_for_status()
  data = {}
  soup = BeautifulSoup(response.content, 'html.parser')
  title = soup.find('title')
  data['title'] = title.string
  data['url'] = url
  meta_list = soup.find_all("meta")
  for meta in meta_list:
    if 'name' in meta.attrs:
        name = meta.attrs['name'].replace(':', '_').lower()
        content = meta.attrs['content'] if 'content' in meta.attrs else ''
        data[name] = content
  print('Metadata extracted successfully.')
  return data

def create_rdf(id, metadata):
  print('Generating rdf from metadata.')
  rdf = f'''
ex:{id} a foaf:Document;
  foaf:title "{metadata['title']}";
  foaf:page "{metadata['url']}" .
  '''
  print('RDF generated successfully.')
  return rdf

def save_rdf(rdf):
  print('Saving RDF into GraphDB.')
  print(rdf)
  api.put_statements(repository_id, rdf_data=rdf)
  print('RDF saved successfully.\n')

def normalize_prefix(term):
  for prefix, value in PREFIXES.items():
    if value in term:
      term = term.replace(value, prefix + ':')
  return term
  
def query_sparql(query):
  print('Querying GraphDB:', query)
  url = f'{conf.host}repositories/{repository_id}?query={urllib.parse.quote_plus(query)}'
  response = requests.get(url)
  response.raise_for_status()
  df = pd.read_csv(io.StringIO(response.text), header=0)
  print('Query executed successfully.')
  if(df.empty):
    return None

  groupby = dict(tuple(df.groupby('s')))
  result = {}

  for subject in groupby:
    subject_normalized = normalize_prefix(subject)
    result[subject_normalized] = {}
    for index, row in groupby[subject].iterrows():
      row = row.to_dict()
      p = normalize_prefix(row['p'])
      o = normalize_prefix(row['o'])
      result[subject_normalized][p] = o
  return result

def check_for_isomorphic_graphs(subject_id):
  print('Checking for isomorphic graphs.')
  query = f'''
    PREFIX ex:<http://example.org/>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    SELECT * WHERE {{ 
      ?s a foaf:Document . 
      ?s ?p ?o . 
      FILTER (?s = {subject_id})
    }}
    LIMIT 100
    '''
  
  target_rdf = query_sparql(query)
  print('Target RDF:', target_rdf)

  comparison_where_clause = ''
  for predicate in target_rdf[subject_id]:
    o = f'"{target_rdf[subject_id][predicate]}"'
    for prefix in PREFIXES:
      if f'{prefix}:' in o:
        o = o.replace('"', '')
    comparison_where_clause += f'      ?s {predicate} {o} . \n'
  
  comparison_query = f'''
    PREFIX ex:<http://example.org/>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    SELECT * WHERE {{
{comparison_where_clause}      ?s ?p ?o .
      FILTER (?s != {subject_id})
    }}
    LIMIT 100
  '''
  result_query = query_sparql(comparison_query)
  print('Isomorphic RDFs:', result_query)

  return result_query

def normalize_url(url):
  normalized_url = url.split('//')[1].replace('/', '_')
  return normalized_url

def search_google(terms):
  print('Searching on Google terms:', terms)
  query = urllib.parse.quote_plus(', '.join(terms))
  response = requests.get("https://www.google.com/search?q=" + query)
  response.raise_for_status()
  links = list(response.html.absolute_links)

  for url in links[:]:
    if 'google' in url:
      links.remove(url)

  return links

def search_duckduckgo(terms, max_results=3):
  results = ddg(', '.join(terms), max_results=max_results)
  return [e['href'] for e in results]