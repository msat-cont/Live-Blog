define(['gizmo', 
        /*'gui/superdesk/livedesk/scripts/js/models/collaborator',
        'gui/superdesk/livedesk/scripts/js/models/post'*/], 
function(giz, Collaborator, Post)
{
    return {init: function(){

        var newSync = $.extend({}, giz.Sync, 
        {
            options: { headers: { 'Authentication': 1 } }
        }),
        X = giz.Model.extend({ dataAdapter: newSync.dataAdapter });
    
    console.log(X.prototype.dataAdapter('http://localhost:8080/resources/my/Superdesk/Collaborator/22').read());

    
    
    //console.clear();
    //giz.Model.options.x = 'y';
    //console.dir('-----', giz.Model.options);
    //var c = new Collaborator('http://localhost:8080/resources/Superdesk/Collaborator/22');
    //var p = new giz.Collection('http://localhost:8080/resources/Superdesk/Collaborator/', Collaborator);

    //    p.get(50).done(function(Colab){ Colab && Colab.remove().sync() });
        
    //p.set({'Source': 1, 'Person': 1})
    //    .sync('http://localhost:8080/resources/Superdesk/Collaborator/')
    //    .done(function(){ console.log(p); });
    
    //c.options.ceva = 'altceva';
    //console.dir('-----', c.options);
    //console.dir('-----', giz.Model.options);
/*    
    console.dir(c);
    
    c.sync().done(function()
    {
        console.log('after sync');
        c.get('Post').get('http://localhost:8080/resources/Superdesk/Post/2').done(function(){ console.log(arguments); });
    });
    setTimeout(function(){ c.sync(); }, 3000);
*/    
    
        /*var Source = Model.extend(),
    Collaborator = Model.extend({ defaults:{ Post: CollaboratorPost }}),
    Post = Model.extend({ defaults:{ Author: Collaborator }}),
    CollaboratorPost = new Collection({ model: Post }),
    Collaborator = Model.extend
    ({ 
        defaults: { Post: CollaboratorPost, Source: Source } 
    });
    
var p = new Post('http://localhost:8080/resources/Superdesk/Post/1'); 
    console.log(p.sync().done(function(){console.log(p)}))
    */
    
    }};
});