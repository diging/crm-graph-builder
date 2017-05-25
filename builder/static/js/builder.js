// TODO: build in a base path.

var ClassList = {
    data: function() {
        return {
            classes: []
        }
    },
    mounted: function() {
        var self = this;
        this.$http.get('/entities').then(function(response) {
            console.log(response);
            self.classes = response.body.classes;
        })
    },
    template: `
        <div class="list-group">
            <a v-on:click="selectClass(class_object)" class="list-group-item" v-for="class_object in classes" v-bind="class_object">{{ class_object.name }}</a>
        </div>
    `,
    methods: {
        selectClass: function(class_object) {
            this.$emit('select_class', class_object);
        }
    }

}

var EntityList = {
    props: ['entity_class'],
    data: function() {
        return {
            entities: []
        }
    },
    mounted: function() {
        var self = this;
        this.$http.get(this.entity_class.url).then(function(response) {
            console.log(response);
            self.entities = response.body.class.instances;
        })
    },
    template: `
        <div class="list-group">
            <a v-on:click="selectEntity(entity)"
                class="list-group-item"
                v-for="entity in entities"
                v-bind="entity">
                {{ entity.entity.value }}
            </a>
        </div>
    `,
    methods: {
        selectEntity: function(entity) {
            this.$emit('select_entity', entity.entity);
        }
    }

}


var PropertyCreator = {
    props: ['property'],
    data: function() {
        return {
            q: null,
            target_class_choices: [],
            target_class_name: null,
            target_class_description: null,
            target_class: null,
            target_entities: [],
            selected_target: null,
            searching: false,
            confidence: 10,
            evidence: null,
            property_description: null,
            saving: false,
            value: null
        }
    },
    mounted: function() {
        this.reset();
    },
    watch: {
        property: function() {
            this.reset();
        }
    },
    template: `
        <div class="panel">
            <div class="panel-heading">
                <div class="h4">{{ property.name }}</div>
                <p class="text-info text-small">{{ property_description }}</p>
            </div>
            <div class="panel-body">
                <div class="form">
                    <div class="row">
                        <div class="col-sm-4">
                            <div class="form-group">
                                <label class="control-label">Target Class</label>
                                 <select class="form-control input-sm"
                                        v-model="target_class_name"
                                        v-on:change="selectTargetClass">
                                        <option v-for="entity_class in target_class_choices"
                                            v-bind:value="entity_class.name">
                                            {{ entity_class.name }}
                                        </option>
                                    </select>
                            </div>
                        </div>
                        <div class="col-sm-8">
                            <div class="form-group">
                                <label class="control-label">Target</label>
                                <div class="input-group">
                                    <span class="input-group-btn">
                                        <a class="btn" v-on:click="resetTarget">
                                            <span v-bind:class="{
                                                    'glyphicon': true,
                                                    'glyphicon-search': !searching && selected_target == null,
                                                    'glyphicon-hourglass': searching,
                                                    'glyphicon-remove': selected_target != null
                                                }"></span>
                                        </a>
                                    </span>
                                    <input class="form-control input-sm" type="search" v-model="q" v-on:input="search" v-bind:disabled="selected_target != null || saving">
                                    <span class="input-group-btn">
                                        <a class="btn btn-success" v-on:click="createTarget">
                                            <span class="glyphicon glyphicon-save">
                                            </span>
                                        </a>
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="row" v-if="selected_target != null">
                        <div class="col-sm-4">
                            <div class="form-group">
                                <label>Confidence</label>
                                <input class="form-control input-sm" type="number" min=0 max=10  v-model="confidence">
                            </div>
                        </div>
                        <div class="col-sm-8">
                            <div class="form-group">
                                <label>Evidence</label>
                                <input class="form-control input-sm" type="url" v-model="evidence">
                            </div>
                        </div>
                    </div>
                    <div class="row" v-if="selected_target != null">
                        <div class="col-sm-10">
                            <div class="form-group">
                                <label>Value</label>
                                <input class="form-control input-sm" type="text" v-model="value">
                            </div>
                        </div>
                        <div class="col-sm-2 text-right">
                            <a class="btn btn-sm btn-success" v-on:click="createProperty">Create</a>
                        </div>
                    </div>
                    <div class="list-group" v-if="target_entities.length > 0">
                        <a class="list-group-item" v-for="entity in target_entities" v-on:click="selectTarget(entity.entity)">{{ entity.entity.value }}</a>
                    </div>
                    <p v-if="target_class_description != null && selected_target == null" class="text-info text-small">
                        {{ target_class_description }}
                    </p>
                </div>
            </div>
        </div>
    `,
    methods: {
        reset: function() {
            this.q = null;
            this.target_entities = [];
            this.selected_target = null;
            this.searching = false;
            this.confidence = 10;
            this.evidence = null;
            this.property_description = null;
            this.saving = false;
            this.value = null;
            var self = this;
            this.$http.get(this.property.url).then(function(response) {
                console.log(response);
                self.property_details = response.body.property;
                self.property_description = self.property_details.description;
                self.target_class_choices = [self.property_details.range];
                self.target_class_choices = self.target_class_choices.concat(self.property_details.range.subclasses);
                self.target_class = self.property_details.range;
                this.target_class_description = self.target_class.description;
                self.target_class_name = self.property_details.range.name;

            });
        },
        selectTargetClass: function() {
            if (this.saving) {
                return;
            }
            var self = this;
            this.target_class_choices.forEach(function(target) {
                if (target.name == self.target_class_name) {
                    self.target_class = target;
                }
            });
            console.log("::", this.target_class);
            this.target_class_description = this.target_class.description;
        },
        search: function() {
            if (this.q.length < 3 || this.saving) {
                this.target_entities = [];
                return;
            }

            var self = this;
            this.searching = true;
            this.$http.get(this.target_class.url + '?value__icontains=' + this.q).then(function(response) {
                self.searching = false;
                self.target_entities = response.body.class.instances;
            }).catch(function(error) {
                self.searching = false;
            });
        },
        selectTarget: function(entity) {
            if (this.saving) {
                return;
            }
            this.selected_target = entity;
            this.target_entities = [];
            this.q = entity.value;
        },
        resetTarget: function() {
            if (this.selected_target == null || this.searching || this.saving) {
                return;
            }
            this.selected_target = null;
            this.q = null;
        },
        createTarget: function() {
            this.saving = true;
            var self = this;
            this.$http.post(this.target_class.url, {'value': this.q}).then(function(response) {
                console.log(response);
                self.selected_target = response.body.entity;
                self.saving = false;
            }).catch(function(error) {
                console.log(error);
                self.saving = false;
            });
        },
        createProperty: function() {
            this.saving = true;
            var payload = {
                value: this.value,
                confidence: this.confidence,
                evidence: this.evidence
            }
            var pth = this.property_details.url + '/' + this.selected_target.id;
            var self = this;
            this.$http.post(pth, payload).then(function(response) {
                self.saving = false;
                console.log(response);
                self.$emit('created_property', response.body.property);
            }).catch(function(error) {
                self.saving = false;
                console.log(error);
            });
        }
    }
}


var EntityDetails = {
    props: ['entity'],
    components: {
        'property-creator': PropertyCreator
    },
    data: function() {
        return {
            details: null,
            properties: [],
            available_properties: [],
            primary_class: {},
            adding_property: false,
            selected_property: null
        }
    },
    watch: {
        entity: function() {
            this.reset();
        }
    },
    mounted: function() {
        this.reset();
    },
    template: `<div class="row">
        <div v-bind:class="{
                'col-sm-12': selected_property == null,
                'col-sm-6': selected_property != null
            }">
            <div>
                This entity is primarily a:
                <a class="btn btn-property btn-xs btn-warning"
                    v-on:click="selectPrimaryClass">
                    {{ primary_class.name }}
                </a>
            </div>
            <div>
                Add property:
                <span class="btn btn-property btn-xs btn-primary"
                    v-for="property_class in available_properties"
                    v-on:click="addProperty(property_class)">
                    {{ property_class.name }}
                </span>
            </div>
            <div class="panel" v-for="property_class in properties" v-bind:property_class=property_class>
                <div class="panel-heading">
                    <div class="h4">{{ property_class.property.name }}</div>
                    <p class="text-info text-small">{{ property_class.property.description }}</p>
                </div>
                <div class="list-group">
                    <div class="clearfix list-group-item" v-for="property in property_class.property.instances" v-bind:property=property>
                        <a class="btn" v-on:click="selectEntity(property.target.entity)">
                            {{ property.value }}: <strong>{{ property.target.entity.instance_of.name }}</strong> {{ property.target.entity.value }}
                        </a>
                        <div class="label-group">
                            <span class="label label-success btn-xs">confidence: {{ property.confidence }}</span>
                            <span class="label label-warning btn-xs">evidence: {{ property.evidence }}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-sm-6" v-if="selected_property != null">
            <property-creator v-bind:property=selected_property v-on:created_property="createdProperty"></property-creator>
        </div>
    </div>`,
    methods: {
        selectPrimaryClass: function() {
            this.$emit('select_class', this.primary_class.url);
            this.$emit('select_entity', this.primary_class.instance_url);
        },
        addProperty: function(property_class) {
            this.adding_property = true;
            this.selected_property = property_class;
        },
        createdProperty: function(property) {
            console.log('got created property', property);
            this.reset();
        },
        reset: function() {
            var self = this;
            this.$http.get(this.entity.url).then(function(response) {
                console.log(response);
                self.details = response.body.entity;
                self.properties = self.details.properties;
                self.available_properties = self.details.available_properties;
                self.primary_class = self.details.primary_class;
            });
            this.adding_property = false;
            this.selected_property = null;
        },
        selectEntity: function(entity) {
            console.log(entity);
            this.$emit('select_class', entity.instance_of.url);
            this.$emit('select_entity', entity);
        }
    }
}

var EntityCreator = {
    props: ['entity_class'],
    data: function() {
        return {
            value: null,
            saving: false
        }
    },
    template: `
        <div class="container">
            <form class="form form-horizontal">
                <div class="form-group">
                    <label class="control-label">Value</label>
                    <div class="input-group">
                        <input type="text" v-model="value" class="form-control">
                        <span class="input-group-btn">
                            <a class="btn btn-success" v-on:click="createEntity">
                                <span class="glyphicon glyphicon-save"></span>&nbsp;
                            </a>
                        </span>
                    </div>
                </div>
            </form>
        </div>
    `,
    methods: {
        createEntity: function() {
            if (this.value == null || this.value.length < 2 || this.saving) {
                return;
            }
            this.saving = true;
            var self = this;
            this.$http.post(this.entity_class.url, {value: this.value}).then(function(response) {
                self.$emit('created_entity', response.body.entity);
                self.saving = false;
            }).catch(function(error){
                console.log(error);
                self.saving = false;
            });
        }
    }
}

var Builder = new Vue({
    el: '#builder',
    data: function() {
        return {
            entity_class: null,
            entity: null,
            property_name: null,
            target_id: null,
            property_id: null,
            adding_property: false,
            creating_entity: false
        }
    },
    components: {
        'class-list': ClassList,
        'entity-list': EntityList,
        'entity-details': EntityDetails,
        'entity-creator': EntityCreator
    },
    template: `
        <div>
            <div class="breadcrumbs">
                <span class="crumb">
                    <a v-on:click="reset">Home</a>
                </span>
                <span v-if="entity_class != null" class="crumb">
                    <a v-on:click="resetEntity">{{ entity_class.name }}</a>
                </span>
                <span v-if="entity != null" class="crumb">
                    <a v-on:click="resetPropertyClass">{{ entity.value }}</a>
                </span>
            </div>
            <class-list v-if="entity_class == null" v-on:select_class="selectClass"></class-list>
            <div v-if="entity_class != null">
                <div v-bind:class="{
                    h2: entity == null,
                    h4: entity != null
                }">{{ entity_class.name }}</div>
                <p v-bind:class="{
                    'text-info': true,
                    'text-small': entity != null
                }">{{ entity_class.description }}</p>
            </div>
            <div class="container" style="margin-bottom: 10px;" v-if="entity_class != null && entity == null && !creating_entity">
                <a class="btn btn-success" v-on:click="startCreatingEntity">
                    <span class="glyphicon glyphicon-plus"></span> Create
                </a>
            </div>
            <entity-creator
                v-if="creating_entity"
                v-bind:entity_class="entity_class"
                v-on:created_entity="createdEntity">
            </entity-creator>
            <div v-if="entity != null">
                <div class="h2">{{ entity.value }}</div>
            </div>
            <entity-list
                v-if="entity_class != null && entity == null"
                v-bind:entity_class=entity_class
                v-on:select_entity="selectEntity">
            </entity-list>
            <entity-details
                v-if="entity != null"
                v-bind:entity=entity
                v-on:select_class="selectClass"
                v-on:select_entity="selectEntity">
            </entity>
        </div>
    `,
    methods: {
        startCreatingEntity: function() { this.creating_entity = true; },
        createdEntity: function(entity) {
            this.creating_entity = false;
            console.log(entity);
            this.selectEntity(entity);
        },
        selectClass: function(class_object) {
            if (typeof(class_object) == 'string') {
                var self = this;
                this.$http.get(class_object).then(function(response) {
                    self.entity_class = response.body.class;
                });
            } else {
                this.entity_class = class_object;
            }

        },
        selectEntity: function(entity) {
            if (typeof(entity) == 'string') {
                var self = this;
                this.$http.get(entity).then(function(response) {
                    self.entity = response.body.entity;
                });
            } else {
                this.entity = entity;
            }
        },
        reset: function() {
            this.entity_class = null;
            this.resetEntity();
        },
        resetEntity: function() {
            this.entity = null;
            this.resetPropertyClass();
        },
        resetPropertyClass: function() {
            this.property_name = null;
            this.target_id = null;
            this.property_id = null;
            this.adding_property = false;
            this.property_class = null;
        }

    }
});
