/**
 * @fileoverview Client side of enhanced JOSN based message passing.
 *
 * @author keith@dartworks.biz (Keith Dart)
 */
// vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab


/**
 * Func_desc
 * @param {String} pname desc.
 * @param {CustomEvent} pname2 desc2.
 * @return {Node} Return_desc.
 */
function XXX(src, ev) {

};

function XXXObj() {
  this.attrib = null;
  this.attrib2 = null;
};

/** 
 * Method_desc.
 * @param {String} parm1 Parm1 desc.
 * @return {String} Return_desc.
 */
XXXObj.prototype.method = function() {

};


    match: function (/* ... */) {
        for (var i = 0; i < this.pairs.length; i++) {
            var pair = this.pairs[i];
            if (pair[1].apply(this, arguments)) {
                return pair[2].apply(this, arguments);
            }
        }
        throw new Error("No replacer found");
    }


function serializeJSON(obj) {

    return JSON.stringify(obj, repl);
}
