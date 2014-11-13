//    Copyright (C) 2011 Keith Dart <keith@dartworks.biz>
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
 * @fileoverview Implement a general purpose pager widget.
 *
 * @author keith@dartworks.biz (Keith Dart)
 */


/**
 * Func_desc
 * @param {String} pname desc.
 * @param {CustomEvent} pname2 desc2.
 * @return {Node} Return_desc.
 */

pager = {
    Pager: function(minimum, maximum, /*opt*/increment) {
        this.increment = increment || 20;
        this.minimum = minimum;
        this.maximum = maximum;
        this.offset  = this.minimum + this.increment;
        this.limit = increment;
        bindMethods(this);
    },
    doNext: function() {
        this.start = Math.min(this.maximum, this.start + this.increment);
        this.limit = Math.min(this.maximum, this.start + this.increment);
        signal(this, "pagernext");
        },
    doPrevious: function() {
        this.current = Math.max(this.begin, this.current - this.increment);
        signal(this, "pagerprevious");
        },
    doEnd: function() {
        this.current = 
        signal(this, "pagerend");
        },
    doBeginning: function() {
        signal(this, "pagerbegin");
        },
    setIncrement: function(inc) {
        this.increment = inc;
        }
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

// vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
