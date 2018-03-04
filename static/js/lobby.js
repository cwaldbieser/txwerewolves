
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
                var value = entry[1];
                var a = $("<a>")
                    .attr("href", "#")
                    .addClass("list-group-item")
                    .addClass("list-group-item-action")
                    .text(label)
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
        if('show-dialog' in o)
        {
            var info = o['show-dialog'];
            var dlg_type = info['dialog-type'];
            if (dlg_type == 'choose-players')
            {
                create_choose_players_dialog(info);
            }
            $("#dialog-collapse").collapse('show');
            $("#actions-collapse").collapse('hide');
        }
        if('hide-dialog' in o)
        {
            $("#dialog-collapse").collapse('hide');
            $("#actions-collapse").collapse('show');
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
            var new_pathname = pathname.substr(0, pathname.lastIndexOf('/')) + 'expire';
            console.log(new_pathname);
            window.location.replace(new_pathname);
        }
    };

    $.get("./lobby/status");
    $.get("./lobby/actions");

    $("#chat-send").click(function(e){
        e.preventDefault();
        var message = $("#chat-message").val();
        $("#chat-message").val("");
        $.post("./chat", {'message': message});
    })
    ;
});

function create_choose_players_dialog(info)
{
    var actions = info['actions'];
    var dialog_body = $("#dialog_body")
        .addClass("list-group-item")
        .addClass("list-group-item-action")
        .empty()
    ;
    $.each(actions, function(i, action){
        var player = action[0];
        var value = action[1];
        var a = $("<a>")
            .attr("href", "#")
            .addClass("list-group-item")
            .addClass("list-group-item-action")
            .text(player)
            .data("command-value", value)
            .click(function(e){
                e.preventDefault();
                $.post("./action", {'command': $(this).data("command-value")})
            })
            .appendTo(dialog_body)
        ;
    })
    ; 
}
