
$(document).ready(function() {
    var source = new EventSource('/subscribe');
    source.onmessage = function(event) {
        console.log(event.data);
        var o = $.parseJSON(event.data);
        if('status' in o)
        {
            var status = o['status'];
            $("#session_status").text(status);
        }
        if('actions' in o)
        {
            $("#actions").empty();
            var actions = o['actions'];
            for(var i=0; i < actions.length; i++)
            {
                var entry = actions[i];
                var label = entry[0];
                var desc = entry[1];
                var value = entry[2];
                var a = $("<a>")
                    .attr("href", "#")
                    .addClass("list-group-item")
                    .addClass("list-group-item-action")
                    .text(desc)
                    .data("command-value", value)
                    .click(function(e){
                        e.preventDefault();
                        $.post("./action", {'command': $(this).data("command-value")})
                    })
                    .appendTo($("#actions"));
            }
        }
        if('chat' in o)
        {
            var e = o['chat'];
            var sender = e['sender'];
            var message = e['message'];
            var li = $("<li>");
            var label = $("<span>")
                .addClass("badge")
                .addClass("badge-primary")
                .text(sender + ": ")
                .appendTo(li)
            ;
            var span = $("<span>")
                .text(message)
                .appendTo(li)
            ;
            li.prependTo($("#chat-output")); 
        }
        if('output' in o)
        {
            var message = o['output'];
            message = message.replace(/\n/g, "<br />");
            var p = $("<li>")
                .html(message)
                .prependTo($("#output"));
        }
        if('install-app' in o)
        {
            var resource = o['install-app'];
            var pathname = window.location.pathname;
            var new_pathname = pathname.substr(0, pathname.lastIndexOf('/')) + resource;
            console.log(new_pathname);
            window.location.replace(new_pathname);
        }
        if('shut-down' in o)
        {
            var pathname = window.location.pathname;
            var new_pathname = pathname.substr(0, pathname.lastIndexOf('/')) + 'logout';
            console.log(new_pathname);
            window.location.replace(new_pathname);
        }
    };

    //$.get("./werewolves/status");
    //$.get("./werewolves/actions");

    $("#chat-send").click(function(e){
        e.preventDefault();
        var message = $("#chat-message").val();
        $("#chat-message").val("");
        $.post("./chat", {'message': message});
    })
    ;
});

