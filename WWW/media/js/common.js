//    Copyright (C) 2010 Keith Dart <keith@dartworks.biz>
//
//    This library is free software; you can redistribute it and/or
//    modify it under the terms of the GNU Lesser General Public
//    License as published by the Free Software Foundation; either
//    version 2.1 of the License, or (at your option) any later version.
//
//    This library is distributed in the hope that it will be useful,
//    but WITHOUT ANY WARRANTY; without even the implied warranty of
//    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
//    Lesser General Public License for more details.

/**
 * @fileoverview File desc.
 *
 * @author keith@dartworks.biz (Keith Dart)
 */


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

JSONReplacers = function () {
    this.pairs = [];
};

MochiKit.Base.AdapterRegistry.prototype = {

    register: function (name, check, wrap, /* optional */ override) {
        if (override) {
            this.pairs.unshift([name, check, wrap]);
        } else {
            this.pairs.push([name, check, wrap]);
        }
    },

    match: function (/* ... */) {
        for (var i = 0; i < this.pairs.length; i++) {
            var pair = this.pairs[i];
            if (pair[1].apply(this, arguments)) {
                return pair[2].apply(this, arguments);
            }
        }
        throw new Error("Replacer not found");
    },

    unregister: function (name) {
        for (var i = 0; i < this.pairs.length; i++) {
            var pair = this.pairs[i];
            if (pair[0] == name) {
                this.pairs.splice(i, 1);
                return true;
            }
        }
        return false;
    }
};


// vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
