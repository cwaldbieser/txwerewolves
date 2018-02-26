
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
        if('player-info' in o)
        {
            var info = o['player-info'];
            var user_id = info['user_id'];
            var dealt_role = info['card_name'];
            $("#user-id")
                .text(user_id)
            ;
            $("#dealt-role")
                .text(dealt_role)
            ; 
        }
        if('game-info' in o)
        {
            var card_counts = o['game-info'];
            var tbl = $("<table>");
            tbl.append(
                $("<tr>")
                    .append($("<th>").text("Card Name"))
                    .append($("<th>").text("Count"))
            );
            for(var i=0; i < card_counts.length; i++)
            {
                var row = card_counts[i];
                var card_name = row[0];
                var count = row[1];
                var tr = $("<tr>").appendTo(tbl);
                $("<td>")
                    .text(card_name)
                    .appendTo(tr)
                ;
                $("<td>")
                    .text("" + count)
                    .appendTo(tr)
                ;
            }
            $("#game-info")
                .empty()
                .append(tbl)
            ;
        }        
        if('phase-info' in o)
        {
            var info = o['phase-info'];
            var title = info[0];
            var desc = info[1];
            var info_block = $("#phase-info");
            info_block.empty();
            $("<h3>")
                .text(title)
                .appendTo(info_block)
            ;
            $("<p>")
                .text(desc)
                .appendTo(info_block)
            ; 
        }
        if('actions' in o)
        {
            $("#actions").empty();
            var actions = o['actions'];
            for(var i=0; i < actions.length; i++)
            {
                var entry = actions[i];
                var desc = entry[0];
                var value = entry[1];
                var selected_message = entry[2];
                var a = $("<a>")
                    .attr("href", "#")
                    .addClass("list-group-item")
                    .addClass("list-group-item-action")
                    .text(desc)
                    .data("command-value", value)
                    .data("selected-message", selected_message)
                    .click(function(e){
                        e.preventDefault();
                        $.post("./action", {'command': $(this).data("command-value")})
                        var myself = $(this);
                        var selected_message = myself.data("selected-message");
                        var p = $("<p>").text(selected_message);
                        $(this).replaceWith(p);
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
            $("#output")
                .empty()
                .html(message)
            ;
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

    $.get("./werewolves/player-info");
    $.get("./werewolves/game-info");
    $.get("./werewolves/output");
    $.get("./werewolves/actions");
    $.get("./werewolves/phase-info");

    $("#chat-send").click(function(e){
        e.preventDefault();
        var message = $("#chat-message").val();
        $("#chat-message").val("");
        $.post("./chat", {'message': message});
    })
    ;
});

