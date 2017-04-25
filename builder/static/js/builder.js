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
        this.$http.get('/entities/' + this.entity_class.name ).then(function(response) {
            console.log(response);
            self.entities = response.body.entities;
        })
    },
    template: `
        <div class="list-group">
            <a v-on:click="selectEntity(entity)" class="list-group-item" v-for="entity in entities" v-bind="entity">{{ entity }}</a>
        </div>
    `,
    methods: {
        selectEntity: function(entity) {
            this.$emit('select_entity', entity);
        }
    }

}

var Builder = new Vue({
    el: '#builder',
    data: function() {
        return {
            entity_class: null,
            entity_id: null,
            property_name: null,
            target_id: null,
            property_id: null
        }
    },
    components: {
        'class-list': ClassList,
        'entity-list': EntityList
    },
    template: `
        <div>
            <div class="breadcrumbs">
                <span class="crumb">Home</span>
                <span v-if="entity_class != null" class="crumb">{{ entity_class.name }}</span>
            </div>
            <class-list v-if="entity_class == null" v-on:select_class="selectClass"></class-list>
            <div v-if="entity_class != null">
                <div class="h2">{{ entity_class.name }}</div>
                <p class="text-info">{{ entity_class.description }}</p>
            </div>
            <entity-list v-if="entity_class != null && entity_id == null" v-bind:entity_class=entity_class></entity-list>
        </div>
    `,
    methods: {
        selectClass: function(class_object) {
            this.entity_class = class_object;
        }
    }
});
