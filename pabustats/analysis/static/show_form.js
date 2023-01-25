
$(document).ready(function() {

          $("[id^=id_rule][id$=0]").click(function() {
                  $("#" + this.id.slice(0, -1) + "1").toggle();
                  $("#" + this.id.slice(0, -1) + "2").toggle();
          });

          $("#id_base_rule_0").change(function() {
                    if (this.value == "") {
                              $("#" + this.id.slice(0, -1) + "1").css("visibility", "hidden");
                              $("#" + this.id.slice(0, -1) + "2").css("visibility", "hidden");
                    } else {
                              $("#" + this.id.slice(0, -1) + "1").css("visibility", "visible");
                              $("#" + this.id.slice(0, -1) + "2").css("visibility", "visible");
                    }
          });

          $(".spoiler-block, .spoiler-content").click(function() {
                    $(this).parent().find(".spoiler-content").toggle()
          });
});

function showLoader(){
      $("#loadingDiv").show();
}

function toggleDetails(){
      $(".details").toggle();
}
