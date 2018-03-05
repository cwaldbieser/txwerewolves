
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
        if('settings-info' in o)
        {
            var settings = o['settings-info'];
            var role_flags = settings['roles'];
            var werewolves = settings['werewolves'];
            $("#id_settings_link").show();
            var tags = ["seer", "robber", "troublemaker", "minion", "insomniac", "hunter", "tanner"];
            for(var i=0; i < tags.length; i++)
            {
                var tag = tags[i];
                var flag = role_flags[tag];
                $("#id_" + tag).prop("checked", flag);
            }
            $("#id_ww_count").find("option[value=" + werewolves + "]").prop("selected", true);
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
            var tbl = $("#game-info-table");
            tbl.find("tr:gt(0)").remove();
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
                var request_actions = false;
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
                        $("#actions")
                            .empty()
                            .append(p)
                        ;
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
            var new_pathname = pathname.substr(0, pathname.lastIndexOf('/')) + 'expire';
            console.log(new_pathname);
            window.location.replace(new_pathname);
        }
        if('post-game-results' in o)
        {
            var pgr = o['post-game-results'];
            var voting_table = pgr['voting-table'];
            var winner_text = pgr['winner-text'];
            var player_role_table = pgr['player-role-table'];
            var table_roles = pgr['table-roles'];
            $("#phase-row").slideUp();
            $("#post-game-row").collapse('show');
            // Winner title.
            $("#winner-heading").text(winner_text);
            // Voting table results.
            var vote_tbl = $("#voting-results");
            vote_tbl.find("tr:gt(0)").remove();
            for(var i=0; i < voting_table.length; i++)
            {
                var row = voting_table[i];
                var player = row[0];
                var eliminated = row[1];
                var voted_for = row[2];
                var tr = $("<tr>")
                    .append($("<td>").text(player))
                    .append($("<td>").text(eliminated ? "Y": ""))
                    .append($("<td>").text(voted_for))
                ;
                vote_tbl.append(tr);
            }
            // Player role results.
            var role_tbl = $("#player-roles");
            role_tbl.find("tr:gt(0)").remove();
            for(var i=0; i < player_role_table.length; i++)
            {
                var row = player_role_table[i];
                var player = row[0];
                var dealt_role = row[1];
                var final_role = row[2];
                var tr = $("<tr>")
                    .append($("<td>").text(player))
                    .append($("<td>").text(dealt_role))
                    .append($("<td>").text(final_role))
                ;
                role_tbl.append(tr);
            }
            // table roles 
            var table_roles_tbl = $("#table-roles");
            table_roles_tbl.find("tr:gt(0)").remove();
            for(var i=0; i < table_roles.length; i++)
            {
                var row = table_roles[i];
                var dealt_role = row[0];
                var final_role = row[1];
                var tr = $("<tr>")
                    .append($("<td>").text(dealt_role))
                    .append($("<td>").text(final_role))
                ;
                table_roles_tbl.append(tr);
            }
        }
    };

    $.get("./werewolves/request-all");

    $("#chat-send").click(function(e){
        e.preventDefault();
        var message = $("#chat-message").val();
        $("#chat-message").val("");
        $.post("./chat", {'message': message});
    })
    ;

    $("#id-settings-reset").click(function(e){
        var tags = ["seer", "robber", "troublemaker", "minion", "insomniac", "hunter", "tanner"];
        var flags = {};
        for(var i=0; i < tags.length; i++)
        {
            var tag = tags[i];
            flags[tag] = $("#id_" + tag).prop("checked");
        }
        var werewolves = parseInt($("#id_ww_count option:selected").val());
        console.log(flags);
        console.log(werewolves);
        var json_string = JSON.stringify({"roles": flags, "werewolves": werewolves});
        console.log(json_string);
        $.post(
            "./settings", 
            json_string,
            function(data, textStatus, jqXHR){
                console.log("textStatus of settings POST: " + textStatus);
            },
            "json"
        )
        ;
    })
    ;
});

