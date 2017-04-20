from flask import Flask, request, abort, url_for
from flask.views import MethodView
from builder import settings

from neomodel import config
config.DATABASE_URL = settings.NEO4J_URL

import sys
sys.path.append('../cidoc-crm-neo4j')   # TODO: package and distribute this.
from crm import models
models.build_model(settings.CRM_URL)

from flask import json

app = Flask(__name__)


def property_url(instance, property_name):
    return url_for('entity_api', class_name=instance.__class__.__name__,
                   node_id=instance.id, property_name=property_name)


def entity_url(instance):
    return url_for('entity_api', class_name=instance.__class__.__name__,
                   node_id=instance.id)


def properties_for_model(model):
    return filter(lambda p: p.startswith('P'), dir(model))




class NodeMethodView(MethodView):
    def _get_entity(self, instance, props=False):
        model = instance.__class__
        _primary_label = instance.primary_label()
        data = {
            'entity': {
                'id': instance.id,
                'value': instance.value,
                'classes': [{
                    'name': cname,
                    'url': url_for('entity_api', class_name=cname, node_id=instance.id)
                } for cname in instance.labels()],
                'primary_class': {
                    'name': _primary_label,
                    'url': url_for('entity_api', class_name=_primary_label, node_id=instance.id)
                },
            }
        }
        if props:
            data['entity'].update({
                'available_properties': [{
                    'name': pname,
                    'url': property_url(instance, pname)
                } for pname in properties_for_model(model)]
            })
        return data

    def _list_classes(self):
        classes = filter(lambda name: name.startswith('E'), dir(models))
        return json.jsonify({
            'classes': [{
                'name': cname,
                'url': url_for('entity_api', class_name=cname),
                'description': getattr(models, cname).__doc__
            } for cname in classes]
        })

    def _list_entities(self, model, class_name, class_data=False):
        nodeset = model.nodes
        query_params = request.args.items()
        for key, value in query_params:
            try:
                nodeset = nodeset.filter(**{key: value})
            except ValueError as E:
                data = {'error': "%s is not a valid field for %s" % (key, class_name)}
                return json.jsonify(data), 400

        data = {
            'entities': [],
        }
        for node in nodeset.all():
            _primary_label = node.primary_label()
            entity = {
                'id': node.id,
                'value': node.value,
                'url': url_for('entity_api', class_name=class_name, node_id=node.id),
                'primary_class': {
                    'name': _primary_label,
                    'url': url_for('entity_api', class_name=_primary_label, node_id=node.id)
                },
            }
            if class_data:
                entity.update({
                    'classes': [{
                        'name': cname,
                        'url': url_for('entity_api', class_name=cname, node_id=node.id)
                    } for cname in node.labels()],
                })
            data['entities'].append(entity)
        return json.jsonify(data)

    @app.errorhandler(404)
    def get(self, class_name=None, node_id=None, property_name=None):
        if class_name is None:
            return self._list_classes()

        model = getattr(models, class_name, None)
        if model is None:
            data = {'error': "I don't know about %s" % class_name}
            return json.jsonify(data), 404

        if node_id is None:    # List all* entities.
            return self._list_entities(model, class_name)
        else:

            node = model(id=node_id)
            try:
                node.refresh()
            except IndexError:
                return json.jsonify({
                    'error': 'No such node'
                }), 404

            if property_name is None:
                return json.jsonify(self._get_entity(node, props=True))
            else:
                if not property_name.startswith('P'):
                    data = {'error': '%s is not a valid property' % property_name}
                    return json.jsonify(data), 404
                relation = getattr(node, property_name)
                if relation is None:
                    data = {'error': '%s is not a valid property' % property_name}
                    return json.jsonify(data), 404

                data = {
                    'property': {
                        'name': property_name,
                        'url': ''
                    },
                    'targets': [{
                        'id': target.id,
                        'value': target.value,
                        'url': entity_url(target),
                        'class': target.__class__.__name__,
                        'primary_class': {
                            'name': target.primary_label(),
                            'url': url_for('entity_api', class_name=target.primary_label(), node_id=target.id)
                        }
                    } for target in relation.all()]
                }
                return json.jsonify(data)


    def post(self, class_name):
        model = getattr(models, class_name, None)
        if model is None:
            return json.jsonify({'error': "I don't know about %s" % class_name})

        data = json.loads(request.data)
        node = model(value=data.get('value'))
        node.save()
        node_data = {
            'id': node.id,
            'value': node.value
        }
        return json.jsonify({
            'entity': node_data,
            'available_properties': filter(lambda p: p.startswith('P'), dir(model))
        })





node_view = NodeMethodView.as_view('entity_api')
app.add_url_rule('/entities', view_func=node_view, methods=['GET'])
app.add_url_rule('/entities/<string:class_name>', view_func=node_view, methods=['GET', 'POST'])
app.add_url_rule('/entities/<string:class_name>/<int:node_id>', view_func=node_view, methods=['GET'])
app.add_url_rule('/entities/<string:class_name>/<int:node_id>/<string:property_name>', view_func=node_view, methods=['GET'])
