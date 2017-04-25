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
            target_class: null,
            target_entities: []
        }
    },
    mounted: function() {
        var self = this;
        this.$http.get(this.property.url).then(function(response) {
            self.property_details = response.body.property;
            self.target_class_choices = [self.property_details.range];
            self.target_class_choices = self.target_class_choices.concat(self.property_details.range.subclasses);
            self.target_class = self.property_details.range.name;
        });
    },
    template: `
        <div class="panel">
            <div class="panel-body">
                <div class="form form-horizontal">
                    <div class="form-group">
                        <label>Target Class</label>
                         <select class="form-control"
                                v-model="target_class">
                                <option v-for="entity_class in target_class_choices" v-bind:value="entity_class.name"">
                                    {{ entity_class.name }}
                                </option>
                            </select>
                    </div>
                    <div class="form-group">
                        <label>Target</label>
                        <input class="form-control" type="text" v-model="q" v-on:input="search">
                    </div>
                    <div class="list-group" v-if="target_entities.length > 0">
                        <div class="list-group-item" v-for="entity in target_entities">{{ entity.entity.value }}</div>
                    </div>
                </div>
            </div>
        </div>
    `,
    methods: {
        search: function() {
            if (this.q.length < 3) {
                this.target_entities = [];
                return;
            }
            var target_class = null;
            var self = this;
            this.target_class_choices.forEach(function(target) {
                if (target.name == self.target_class) target_class = target;
            });
            this.$http.get(target_class.url + '?value__icontains=' + this.q).then(function(response) {
                self.target_entities = response.body.class.instances;
                console.log(self.target_entities);
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
    mounted: function() {
        var self = this;
        this.$http.get(this.entity.url).then(function(response) {
            self.details = response.body.entity;
            self.properties = self.details.properties;
            self.available_properties = self.details.available_properties;
            self.primary_class = self.details.primary_class;
        });
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
                    <div class="h4">{{ property_class.name }}</div>
                    <p class="text-info">{{ property_class.description }}</p>
                </div>
                <div class="list-group">
                    <div class="clearfix list-group-item" v-for="property in property_class.instances" v-bind:property=property>
                        <div>
                            {{ property.value }}: <strong>{{ property.target.entity.instance_of.name }}</strong> {{ property.target.entity.value }}
                        </div>
                        <div class="label-group">
                            <span class="label label-success btn-xs">confidence: {{ property.confidence }}</span>
                            <span class="label label-warning btn-xs">evidence: {{ property.evidence }}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-sm-6" v-if="selected_property != null">
            <property-creator v-bind:property=selected_property></property-creator>
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
            adding_property: false
        }
    },
    components: {
        'class-list': ClassList,
        'entity-list': EntityList,
        'entity-details': EntityDetails
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
