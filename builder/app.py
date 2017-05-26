from urlparse import urljoin
from flask import Flask, request, abort, url_for, redirect, render_template, flash, json
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required

from flask.views import MethodView
from builder import settings
from builder.oauth import OAuthSignIn, GitHubSignin
import optparse

from neomodel import config
import neomodel
config.DATABASE_URL = settings.NEO4J_URL

from crm import models


fields = {
    'value': lambda: neomodel.StringProperty(index=True, unique=True),
    'created': lambda: neomodel.DateTimeProperty(default_now=True),
    'created_by': lambda: neomodel.StringProperty(index=True),
}
rel_fields = {
    'value': neomodel.StringProperty,
    'evidence': neomodel.StringProperty,
    'confidence': neomodel.FloatProperty,
    'created': lambda: neomodel.DateTimeProperty(default_now=True),
    'created_by': neomodel.StringProperty,
    'updated': neomodel.DateTimeProperty,
}
models.build_models(settings.CRM_URL, fields=fields, rel_fields=rel_fields)

app = Flask(__name__, static_url_path=settings.STATIC_URL)
app.config['SECRET_KEY'] = settings.SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = settings.SQLALCHEMY_DATABASE_URI
app.config['OAUTH_CREDENTIALS'] = settings.OAUTH_CREDENTIALS
app.config['STATIC_URL'] = settings.STATIC_URL
app.config['ADMIN_SOCIALID'] = settings.ADMIN_SOCIALID
app.config['ADMIN_NICKNAME'] = settings.ADMIN_NICKNAME
app.config['SERVER_NAME'] = settings.SERVER_NAME

db = SQLAlchemy(app)
lm = LoginManager(app)
lm.login_view = 'index'


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    social_id = db.Column(db.String(64), nullable=False, unique=True)
    nickname = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(64), nullable=True)
    real_name = db.Column(db.String(128), nullable=True)
    homepage = db.Column(db.String(255), nullable=True)
    active = db.Column(db.Boolean, default=False)
    admin = db.Column(db.Boolean, default=False)


@lm.user_loader
def load_user(id):
    return User.query.get(int(id))


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index', _external=True))


@app.route('/authorize/<provider>')
def oauth_authorize(provider):
    print url_for('index', _external=True)
    if not current_user.is_anonymous:
        return redirect(url_for('index', _external=True))
    oauth = OAuthSignIn.get_provider(provider)
    return oauth.authorize()


@app.route('/callback/<provider>')
def oauth_callback(provider):
    print url_for('index', _external=True)
    if not current_user.is_anonymous:
        return redirect(url_for('index', _external=True))
    oauth = OAuthSignIn.get_provider(provider)
    data = oauth.callback()
    if data is None:
        flash('Authentication failed.')
        return redirect(url_for('index', _external=True))
    user = User.query.filter_by(social_id=data['social_id']).first()
    if not user:
        user = User(social_id=data['social_id'],
                    nickname=data['username'],
                    email=data['email'],
                    real_name=data['real_name'],
                    homepage=data['homepage'])
        db.session.add(user)
        db.session.commit()
    login_user(user, True)
    return redirect(url_for('index', _external=True))


@app.route('/user/<userid>')
@app.errorhandler(403)
@login_required
def user(userid):
    if not current_user.admin:
        return 'Nope.', 403
    user = User.query.get(int(userid))
    if user is None:
        return json.jsonify({'error': 'No such user'}), 404
    return json.jsonify({
        'social_id': user.social_id,
        'real_name': user.real_name,
        'nickname': user.nickname,
        'email': user.email,
        'homepage': user.homepage,
        'admin': user.admin,
        'active': user.active
    })


@app.route('/user')
@app.errorhandler(403)
@login_required
def users():
    if not current_user.admin:
        return 'Nope.', 403
    return json.jsonify({
        'users': [
            {
                'id': user.id,
                'social_id': user.social_id,
                'real_name': user.real_name,
                'nickname': user.nickname,
                'email': user.email,
                'homepage': user.homepage,
                'admin': user.admin,
                'active': user.active
            }
        for user in User.query.all()]
    })


@app.route('/user/<userid>/activate')
@app.errorhandler(403)
@login_required
def activate_user(userid):
    if not current_user.admin:
        return 'Nope.', 403
    user = User.query.get(int(userid))
    user.active = True
    db.session.commit()
    return json.jsonify({
        'id': user.id,
        'social_id': user.social_id,
        'real_name': user.real_name,
        'nickname': user.nickname,
        'email': user.email,
        'homepage': user.homepage,
        'admin': user.admin,
        'active': user.active
    })


@app.route('/')
def index():
    return render_template('builder.html', user=current_user)
    # if current_user.is_anonymous:
    #     return "You should probably log in"
    # if current_user.active:
    #     # return redirect(url_for('oauth_authorize', provider='github'))
    #
    # return "Almoster there, %s: You're not active yet" % current_user.real_name

# We may need to load a node without knowing its original class.
BASE_CLASS = models.E1CrmEntity


def property_url(instance, property_name):
    return url_for('entity_api', class_name=instance.__class__.__name__,
                   node_id=instance.id, property_name=property_name)


def property_url_target(instance, property_name, target_id):
    return url_for('entity_api', class_name=instance.__class__.__name__,
                   node_id=instance.id, property_name=property_name,
                   target_id=target_id)

def property_url_instance(instance, property_name, target_id, property_id):
    return url_for('entity_api', class_name=instance.__class__.__name__,
                   node_id=instance.id, property_name=property_name,
                   target_id=target_id, property_id=property_id)


def entity_url(instance):
    return url_for('entity_api', class_name=instance.__class__.__name__,
                   node_id=instance.id)


def properties_for_model(model):
    return filter(lambda p: p.startswith('P'), dir(model))


def get_subclasses(e_class):
    return map(lambda c_name: getattr(models, c_name),
               filter(lambda c_name: e_class in getattr(models, c_name).mro() and e_class.__name__ != c_name,
                      filter(lambda c_name: c_name.startswith('E'), dir(models))))


def get_node(model, node_id):
    """
    Retrieve a data node as an instance of ``model``. If no such node is found,
    returns ``None``.
    """
    node = model(id=node_id)
    try:
        node.refresh()
        return node
    # neomodel looks for nodes with label corresponding to ``model``.
    except IndexError:
        return None


class Serializer(object):
    """
    Base class for serializers. This is probably not necessary, but we can think
    of this as a theoretical interface.
    """
    def __init__(self, instance=None, **kwargs):
        self.instance = instance
        for key, value in kwargs.iteritems():
            if hasattr(self, key) and not key.startswith('_'):
                continue
            setattr(self, key, value)

    def to_json(self, *args, **kwargs):
        raise NotImplementedError('Serializer is just an interface')

    def create(self, *args, **kwargs):
        raise NotImplementedError('Serializer is just an interface')

    def update(self, *args, **kwargs):
        raise NotImplementedError('Serializer is just an interface')


class ClassSerializer(Serializer):
    def to_json(self, raw=False, include_subclasses=True):
        if isinstance(self.instance, list):
            return json.jsonify({
                'classes': [ClassSerializer(instance).to_json(raw=True) for instance in self.instance]
            })

        # Single instance.
        data = {
            'name': self.instance.__name__,
            'url': url_for('entity_api', class_name=self.instance.__name__),
            'description': self.instance.__doc__,

        }
        if include_subclasses:
            data.update({
                'subclasses': [
                    ClassSerializer(class_obj).to_json(raw=True, include_subclasses=False)
                    for class_obj in get_subclasses(self.instance)
                ]
            })
        if raw:
            return data
        return json.jsonify(data)

    def create(self, *args, **kwargs):
        raise NotImplementedError('Nope')

    def update(self, *args, **kwargs):
        raise NotImplementedError('Nope')


class PropertySerializer(Serializer):
    def _single_property(self, include_source=True, include_target=True,
                         include_description=True):
        """
        Generate response data for a single property.
        """
        source = self.instance.start_node()
        target = self.instance.end_node()
        data = {
            'property': {
                'id': self.instance.id,
                'url': property_url_instance(source, self.property_name,
                                             target.id, self.instance.id),
                'instance_of': {
                    'name': self.instance.__class__.__name__,
                    'url': property_url(source, self.property_name)
                }
            }
        }
        for key in rel_fields.keys():
            data['property'][key] = getattr(self.instance, key, None)

        if include_source:
            source = self.instance.start_node()
            data['property'].update({
                'source': EntitySerializer(source).to_json(raw=True),
            })
        if include_target:
            target = self.instance.end_node()
            data['property'].update({
                'target': EntitySerializer(target).to_json(raw=True),
            })
        if include_description:
            data['property']['instance_of'].update({
                'description': self.instance.description
            })
        return data

    def _property_list(self):
        """
        Generate response data for a list of properties.
        """
        instances = [
            PropertySerializer(rel, property_name=self.property_name)\
                .to_json(raw=True, include_source=False,
                         include_target=False, include_description=False)
            for rel in self.instance
        ]
        description = self.instance[0].description
        return instances, description

    def _properties_on_source(self):
        """
        Generate response data for multiple properties of a given class on the
        source node.
        """
        def _get_property(target):
            """Helper function to retrieve property data."""
            _rel = self.instance.all_relationships(target)[0]
            _data = PropertySerializer(_rel, property_name=self.property_name)\
                        .to_json(raw=True, include_source=False,
                                 include_description=False)
            return _data['property']

        if isinstance(self.instance, list):
            # The client may have specified which properties to list.
            instances, description = self._property_list()
        else:    # All target nodes from this source for this property class.
            instances = map(_get_property, self.instance.all())
            _rel_model = self.instance.definition.get('model')
            description = _rel_model.description

        data = {
            'property': {
                'name': self.property_name,
                'url': property_url(self.source, self.property_name),
                'description': description,
                'instances': instances,
                'range': ClassSerializer(self.instance.definition['node_class']).to_json(raw=True),
                'source': EntitySerializer(self.source).to_json(raw=True),
            }
        }
        if hasattr(self, 'target'):
            data.update({
                'target': EntitySerializer(self.target).to_json(raw=True),
                'url': property_url_target(self.source, self.property_name, self.target.id)
            })
        return data

    def to_json(self, raw=False, include_source=True, include_target=True, include_description=False):
        if isinstance(self.instance, neomodel.StructuredRel):
            data = self._single_property(include_source, include_target,
                                         include_description)
        elif isinstance(self.instance, neomodel.RelationshipManager) \
        or isinstance(self.instance, list):
            data = self._properties_on_source()
        if raw:
            return data
        return json.jsonify(data)

    def create(self, data):
        if any([self.source is None, self.property_name is None,
                self.target is None]):
            raise ValueError('Must provide source and property name')
        data = json.loads(data)
        property_manager = getattr(self.source, self.property_name)

        return property_manager.connect(self.target,
                                        properties={
                                            key: data.get(key)
                                            for key in rel_fields.keys()
                                        })

    def update(self, data):
        if any([self.source is None, self.property_name is None,
                self.target is None]):
            raise ValueError('Must provide source and property name')
        data = json.loads(data)
        for key in rel_fields.keys():
            if key not in data:
                continue
            setattr(self.instance, key, data.get(key))
        self.instance.save()
        return self.instance


class EntitySerializer(Serializer):
    def to_json(self, props=False, all_classes=False, raw=False, include_instances=True):
        if isinstance(self.instance, list):
            data = {
                'class': {
                    'name': self.model.__name__,
                    'url': url_for('entity_api', class_name=self.model.__name__),
                    'description': self.model.__doc__,
                    'instances': [EntitySerializer(node).to_json(raw=True)
                                 for node in self.instance],
                    'subclasses': [ClassSerializer(class_obj).to_json(raw=True) for class_obj in get_subclasses(self.model)]
                }
            }
            if raw:
                return data
            return json.jsonify(data)

        model = self.instance.__class__
        _primary_label = self.instance.primary_label()
        _class_name = self.instance.__class__.__name__
        data = {
            'entity': {
                'id': self.instance.id,
                'url': url_for('entity_api', class_name=_class_name,
                               node_id=self.instance.id),
                'primary_class': {
                    'name': _primary_label,
                    'url': url_for('entity_api', class_name=_primary_label),
                    'instance_url': url_for('entity_api',
                                            class_name=_primary_label,
                                            node_id=self.instance.id)
                },
                'instance_of': {
                    'name': _class_name,
                    'url': url_for('entity_api', class_name=_class_name)
                }
            }
        }
        for key in fields.keys():
            data['entity'][key] = getattr(self.instance, key, None)

        if all_classes:
            data['entity'].update({
                'classes': [{
                    'name': cname,
                    'url': url_for('entity_api', class_name=cname,
                                   node_id=self.instance.id)
                } for cname in self.instance.labels()],
            })
        if props:
            data['entity'].update({
                'available_properties': [{
                        'name': pname,
                        'url': property_url(self.instance, pname)
                    } for pname in properties_for_model(model)],
                'properties': property_data(self.instance)
            })
        if raw:
            return data
        return json.jsonify(data)

    def create(self, model, data):
        data = json.loads(data)
        data = {key: data.get(key) for key in fields.keys()}
        node = model(**data)
        node.save()
        return node

    def update(self, data):
        data = json.loads(data)
        for key in fields.keys():
            if key not in data:
                continue
            setattr(self.instance, key, data.get(key))
        self.instance.save()
        return self.instance


def property_data(instance):
    prop_data = []
    for prop in properties_for_model(instance.__class__):
        relation = getattr(instance, prop)
        if len(relation.all()) == 0:
            continue
        serializer = PropertySerializer(relation, source=instance, property_name=prop)
        prop_data.append(serializer.to_json(raw=True, include_source=False))

    return prop_data


class NodeMethodView(MethodView):
    def _list_entities(self, model, class_name, class_data=False):
        nodeset = model.nodes
        for key, value in request.args.items():
            try:
                nodeset = nodeset.filter(**{key: value})
            except ValueError as E:
                data = {
                    'error': "%s is not a valid field for %s"\
                              % (key, class_name)
                }
                return json.jsonify(data), 400

        return EntitySerializer(nodeset.all(), model=model).to_json()

    @app.errorhandler(404)
    def get(self, class_name=None, node_id=None, property_name=None,
            target_id=None, property_id=None):
        """
        Handles all GET requests for the API, ranging from entity class
        descriptions to specific entity properties.
        """
        if class_name is None:  # When no class is specified, list them all.
            data = map(lambda name: getattr(models, name),
                       filter(lambda name: name.startswith('E'), dir(models)))
            return ClassSerializer(data).to_json()

        model = getattr(models, class_name, None)
        if model is None:
            return json.jsonify({'error': "No such class"}), 404

        if node_id is None:
            # When a class is specified by no specific entity, list all entities
            #  that instantiate the class.
            return self._list_entities(model, class_name)

        node = get_node(model, node_id)
        if node is None:
            return json.jsonify({'error': 'No such entity'}), 404

        if property_name is None:
            # No specific property has been specified, so return details about
            #  this particular entity.
            return EntitySerializer(node).to_json(props=True)

        if not property_name.startswith('P'):
            data = {'error': '%s is not a valid property' % property_name}
            return json.jsonify(data), 404

        relation = getattr(node, property_name)
        if relation is None:
            data = {'error': '%s is not a valid property' % property_name}
            return json.jsonify(data), 404

        if target_id is None:    # Get data for this entity and property.
            return PropertySerializer(relation, source=node, property_name=property_name).to_json()

        target_node = get_node(BASE_CLASS, target_id)
        if target_node is None:
            return json.jsonify({'error': 'No such node'}), 404
        target_node = target_node.downcast()    # Get the original entity class.

        if property_id is None:
            try:
                _relations = relation.all_relationships(target_node)
                if not _relations:
                    raise ValueError('No relations')
            except ValueError:
                return json.jsonify({'error': 'No such path'}), 404

            return PropertySerializer(_relations, source=node,
                                      property_name=property_name,
                                      target=target_node).to_json()

        property_instance = filter(lambda rel: rel.id == property_id,
                                   relation.all_relationships(target_node))
        if len(property_instance) == 0:
            return json.jsonify({'error': 'No such property'}), 404
        property_instance = property_instance[0]
        serializer = PropertySerializer(property_instance, source=node,
                                        property_name=property_name,
                                        target=target_node)
        return serializer.to_json(include_description=True)

    @app.errorhandler(405)
    @app.errorhandler(404)
    @login_required
    def put(self, class_name=None, node_id=None, property_name=None,
            target_id=None, property_id=None):
        """
        Handles update for both entities and properties.
        """
        if class_name is None:
            return json.jsonify({'error': 'Not allowed'}), 405

        model = getattr(models, class_name, None)
        if model is None:
            data = {'error': "I don't know about %s" % class_name}
            return json.jsonify(data), 404

        if node_id is None:     # Client is probably attempting a POST request.
            return json.jsonify({'error': 'Not allowed'}), 405

        node = get_node(model, node_id)
        if node is None:
            return json.jsonify({'error': 'No such entity'}), 404

        # If no property (class nor instance) is specified, we're updating the
        #  entity itself.
        if node_id and property_name is None:
            node = EntitySerializer(node).update(request.data)
            return EntitySerializer(node).to_json()

        if target_id is None:   # Client is probably attempting a POST request.
            return json.jsonify({'error': 'Not allowed'}), 405

        # We need at least to know what property class we're dealing with.
        property_manager = getattr(node, str(property_name))
        if property_name is None or property_manager is None:
            return json.jsonify({'error': 'No such property'}), 404

        # And the target must be explicitly specified.
        target = get_node(BASE_CLASS, target_id)
        if target_id is None or target is None:
            return json.jsonify({'error': 'No such entity'}), 404
        target = target.downcast()

        pkwargs = dict(source=node, target=target, property_name=property_name)

        # neomodel doesn't provide any obvious way to retrieve a
        #  relation (what we're calling a property instance) by its id.
        #  So we get all relations from the source to the target, and
        #  pop the one with the matching identifier.
        _rels = property_manager.all_relationships(target)
        property_instance = filter(lambda r: r.id == property_id, _rels)
        if len(property_instance) == 0:
            return json.jsonify({'error': 'No such property'}), 404
        property_instance = property_instance[0]

        try:
            serializer = PropertySerializer(property_instance, **pkwargs)
            property_instance = serializer.update(request.data)
        except ValueError:
            data = {'error': 'Invalid target for this property'}
            return json.jsonify(data), 404
        serializer = PropertySerializer(property_instance, **pkwargs)
        return serializer.to_json(include_description=True)

    @app.errorhandler(405)
    @app.errorhandler(404)
    @login_required
    def post(self, class_name=None, node_id=None, property_name=None,
             target_id=None, property_id=None):
        """
        Handles create for both entities and properties.
        """
        if class_name is None:
            return json.jsonify({'error': 'Not allowed'}), 405

        model = getattr(models, str(class_name), None)
        if model is None:
            data = {'error': "I don't know about %s" % class_name}
            return json.jsonify(data), 404

        # If no node is specified, use the POST data to create a new entity.
        if node_id is None:
            node = EntitySerializer().create(model, request.data)
            return EntitySerializer(node).to_json()

        if property_id or (node_id and not property_name):
            # Client is probably attempting a PUT request.
            return json.jsonify({'error': 'Not allowed'}), 405

        node = get_node(model, node_id)
        if node is None:
            return json.jsonify({'error': 'No such entity'}), 404

        # We need at least to know what property class we're dealing with.
        property_manager = getattr(node, str(property_name))
        if property_name is None or property_manager is None:
            return json.jsonify({'error': 'No such property'}), 404

        # And the target must be explicitly specified.
        target = get_node(BASE_CLASS, target_id)
        if target_id is None or target is None:
            return json.jsonify({'error': 'No such entity'}), 404
        target = target.downcast()

        pkwargs = dict(source=node, target=target, property_name=property_name)
        try:
            serializer = PropertySerializer(**pkwargs)
            property_instance = serializer.create(request.data)
        except ValueError:
            data = {'error': 'Invalid target for this property'}
            return json.jsonify(data), 404
        serializer = PropertySerializer(property_instance, **pkwargs)
        return serializer.to_json(include_description=True)


# @app.endpoint('static')
# def static(filename):
#     static_url = app.config.get('STATIC_URL')
#
#     if static_url:
#         return redirect(urljoin(static_url, filename))
#     return app.send_static_file(filename)


# We're allowing both PUT and POST on views in which they should be mutually
#  exclusive; this is because ``url_for`` qualifies URL resolution with the
#  current method. We therefore explicitly raise 405 inside the put() and post()
#  methods on the view when it looks like the wrong verb was used.
node_view = NodeMethodView.as_view('entity_api')
app.add_url_rule('/entities', view_func=node_view, methods=['GET'])
app.add_url_rule('/entities/<string:class_name>', view_func=node_view,
                 methods=['GET', 'POST', 'PUT'])
app.add_url_rule('/entities/<string:class_name>/<int:node_id>',
                 view_func=node_view, methods=['GET', 'POST', 'PUT'])
app.add_url_rule("/entities/<string:class_name>/<int:node_id>"
                 "/<string:property_name>",  view_func=node_view,
                 methods=['GET', 'POST', 'PUT'])
app.add_url_rule("/entities/<string:class_name>/<int:node_id>"
                 "/<string:property_name>/<int:target_id>", view_func=node_view,
                 methods=['GET', 'POST', 'PUT'])
app.add_url_rule("/entities/<string:class_name>/<int:node_id>"
                 "/<string:property_name>/<int:target_id>/<int:property_id>",
                 view_func=node_view, methods=['GET', 'POST', 'PUT'])



@app.cli.command('initdb')
def initialize_database():
    db.create_all()


@app.cli.command('createadmin', with_appcontext=False)
def create_admin():
    social_id = app.config.get('ADMIN_SOCIALID')
    nickname = app.config.get('ADMIN_NICKNAME')
    user = User.query.filter_by(social_id=social_id).first()
    if not user:
        user = User(social_id=social_id,
                    nickname=nickname)
        db.session.add(user)
        db.session.commit()
    user.admin = True
    user.active = True
    db.session.commit()


@app.cli.command('promote')
def promote():
    import os
    userid = int(os.environ.get('PROMOTE', -1))
    if userid > 0:
        user = User.query.get(userid)
        user.admin = True
        user.active = True
        db.session.commit()
