
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
        //var li = $("<li>")
        //    .text(event.data)
        //    .appendTo($("#output"));
    };

    $.get("./lobby/status");
    $.get("./lobby/actions");
});

function create_choose_players_dialog(info)
{
    var actions = info['actions'];
    //id=dialog_body
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
