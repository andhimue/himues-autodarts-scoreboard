// Frontend/static/js/show_segment.js

/**
 * @summary Zeichnet ein einzelnes Dart-Segment (z.B. die "20") als SVG-Grafik.
 * @param {string} targetSegment Das zu zeichnende Segment (z.B. '20', 'Bull').
 * @param {string} mode Der zu hervorhebende Teil des Segments ('Single', 'Double', 'Triple', 'Full').
 */
 
function drawTargetSegment(targetSegment, mode) {
    UI.focusSegmentGraphic.empty();
    if (!targetSegment || targetSegment === '?' || targetSegment === 'N/A' || targetSegment === 'Game Over') {
        return;
    }
    
    // Lese ALLE Stil-Werte aus dem CSS
    const style = getComputedStyle(UI.focusSegmentGraphic[0]);
    const highlightColor = style.getPropertyValue('--highlight-color').trim();
    const greenColors = {
        single: style.getPropertyValue('--segment-color-green-s').trim(),
        doubleTriple: style.getPropertyValue('--segment-color-green-dt').trim()
    };
    const redColors = {
        single: style.getPropertyValue('--segment-color-red-s').trim(),
        doubleTriple: style.getPropertyValue('--segment-color-red-dt').trim()
    };
    const bullColors = {
        single: style.getPropertyValue('--bull-color-outer').trim(),
        double: style.getPropertyValue('--bull-color-inner').trim()
    };
    const bullRadius = parseFloat(style.getPropertyValue('--bull-radius'));
    const bullseyeRadius = parseFloat(style.getPropertyValue('--bullseye-radius'));

    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    const segmentRotation = { '20': -90, '1': -72, '18': -54, '4': -36, '13': -18, '6': 0, '10': 18, '15': 36, '2': 54, '17': 72, '3': 90, '19': 108, '7': 126, '16': 144, '8': 162, '11': 180, '14': 198, '9': 216, '12': 234, '5': 252 };
    
    function createBlinkingOverlay(originalElement, parentGroup) {
        const overlay = originalElement.cloneNode(true);
        overlay.setAttribute('fill', highlightColor);
        overlay.setAttribute('stroke', 'none');
        overlay.classList.add('blinking-overlay');
        parentGroup.appendChild(overlay);
    }

    if (targetSegment === 'Bull' || targetSegment === '25' || targetSegment === 'Bullseye') {
        svg.setAttribute("viewBox", "-20 -20 40 40");
        const outerBull = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        outerBull.setAttribute("r", bullRadius); // Nutzt CSS-Variable
        outerBull.setAttribute("fill", bullColors.single);
        const innerBull = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        innerBull.setAttribute("r", bullseyeRadius); // Nutzt CSS-Variable
        innerBull.setAttribute("fill", bullColors.double);
        svg.appendChild(outerBull);
        svg.appendChild(innerBull);
        let blinkOuter = false, blinkInner = false;
        if (mode === 'Full' || targetSegment === '25') { blinkOuter = true; blinkInner = true; }
        else if (mode === 'Single' || mode === 'Outer Single') { blinkOuter = true; }
        else if (mode === 'Double' || mode === 'Triple' || targetSegment === 'Bullseye') { blinkInner = true; }
        if (blinkOuter) {
            const outerOverlay = outerBull.cloneNode(true);
            outerOverlay.setAttribute('fill', highlightColor);
            outerOverlay.classList.add('blinking-overlay');
            svg.appendChild(outerOverlay);
            svg.appendChild(innerBull.cloneNode(true));
        }
        if (blinkInner) { createBlinkingOverlay(innerBull, svg); }
    } else {
        const length = parseInt(style.getPropertyValue('--segment-draw-size'), 10) || 108;
        svg.setAttribute("viewBox", "-110 -110 220 220");

        const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
        const rotation = segmentRotation[targetSegment] || 0;
        const translation = -length * 0.55;
        g.setAttribute('transform', `rotate(${rotation}) translate(${translation}, 0)`);

        const greenSegments = ['1', '4', '6', '15', '17', '19', '16', '11', '9', '5'];
        const isGreen = greenSegments.includes(targetSegment);
        const colors = isGreen ? greenColors : redColors;
        const angle = 9 * (Math.PI / 180);
        const paths = {
            double: `M ${length*0.925*Math.cos(-angle)} ${length*0.925*Math.sin(-angle)} A ${length*0.925} ${length*0.925} 0 0 1 ${length*0.925*Math.cos(angle)} ${length*0.925*Math.sin(angle)} L ${length*1.0*Math.cos(angle)} ${length*1.0*Math.sin(angle)} A ${length*1.0} ${length*1.0} 0 0 0 ${length*1.0*Math.cos(-angle)} ${length*1.0*Math.sin(-angle)} Z`,
            outerSingle: `M ${length*0.635*Math.cos(-angle)} ${length*0.635*Math.sin(-angle)} A ${length*0.635} ${length*0.635} 0 0 1 ${length*0.635*Math.cos(angle)} ${length*0.635*Math.sin(angle)} L ${length*0.925*Math.cos(angle)} ${length*0.925*Math.sin(angle)} A ${length*0.925} ${length*0.925} 0 0 0 ${length*0.925*Math.cos(-angle)} ${length*0.925*Math.sin(-angle)} Z`,
            triple: `M ${length*0.56*Math.cos(-angle)} ${length*0.56*Math.sin(-angle)} A ${length*0.56} ${length*0.56} 0 0 1 ${length*0.56*Math.cos(angle)} ${length*0.56*Math.sin(angle)} L ${length*0.635*Math.cos(angle)} ${length*0.635*Math.sin(angle)} A ${length*0.635} ${length*0.635} 0 0 0 ${length*0.635*Math.cos(-angle)} ${length*0.635*Math.sin(-angle)} Z`,
            innerSingle: `M ${length*0.158*Math.cos(-angle)} ${length*0.158*Math.sin(-angle)} A ${length*0.158} ${length*0.158} 0 0 1 ${length*0.158*Math.cos(angle)} ${length*0.158*Math.sin(angle)} L ${length*0.56*Math.cos(angle)} ${length*0.56*Math.sin(angle)} A ${length*0.56} ${length*0.56} 0 0 0 ${length*0.56*Math.cos(-angle)} ${length*0.56*Math.sin(-angle)} Z`
        };
        const doubleArc = $(document.createElementNS("http://www.w3.org/2000/svg", "path")).attr("d", paths.double).attr('fill', colors.doubleTriple);
        const outerSingleArc = $(document.createElementNS("http://www.w3.org/2000/svg", "path")).attr("d", paths.outerSingle).attr('fill', colors.single);
        const tripleArc = $(document.createElementNS("http://www.w3.org/2000/svg", "path")).attr("d", paths.triple).attr('fill', colors.doubleTriple);
        const innerSingleArc = $(document.createElementNS("http://www.w3.org/2000/svg", "path")).attr("d", paths.innerSingle).attr('fill', colors.single);
        
        $(g).append(doubleArc, outerSingleArc, tripleArc, innerSingleArc);
        svg.appendChild(g);

        if (mode === 'Double') createBlinkingOverlay(doubleArc[0], g);
        if (mode === 'Triple') createBlinkingOverlay(tripleArc[0], g);
        if (mode === 'Outer Single') createBlinkingOverlay(outerSingleArc[0], g);
        if (mode === 'Single') { createBlinkingOverlay(outerSingleArc[0], g); createBlinkingOverlay(innerSingleArc[0], g); }
        if (mode === 'Full') { createBlinkingOverlay(doubleArc[0], g); createBlinkingOverlay(outerSingleArc[0], g); createBlinkingOverlay(tripleArc[0], g); createBlinkingOverlay(innerSingleArc[0], g); }
    }
    UI.focusSegmentGraphic.append(svg);
}

//------------------------------------------------------------------

/**
 * @summary Zeichnet die konzentrischen Doppel- oder Triple-Ringe als SVG-Grafik (z.B. für Bermuda).
 * @param {string} mode Welcher Ring hervorgehoben werden soll ('Double' oder 'Triple').
 */
 
function drawTargetRings(mode) {
    UI.focusSegmentGraphic.empty();

    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "-105 -105 210 210");

    const style = getComputedStyle(UI.focusSegmentGraphic[0]);
    const doubleRadius = parseFloat(style.getPropertyValue('--double-ring-radius'));
    const tripleRadius = parseFloat(style.getPropertyValue('--triple-ring-radius'));
    const strokeWidth = parseFloat(style.getPropertyValue('--ring-stroke-width'));
    const highlightColor = style.getPropertyValue('--highlight-color').trim();
    const redColor = style.getPropertyValue('--segment-color-red-dt').trim();
    const greenColor = style.getPropertyValue('--segment-color-green-dt').trim();

    function createSegmentedRing(radius, color, offset = false) {
        const ring = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        const circumference = 2 * Math.PI * radius;
        const segmentArcLength = circumference / 20;
        ring.setAttribute("r", radius);
        ring.setAttribute("fill", "none");
        ring.setAttribute("stroke", color);
        ring.setAttribute("stroke-width", strokeWidth);
        ring.setAttribute("stroke-dasharray", `${segmentArcLength} ${segmentArcLength}`);
        if (offset) {
            ring.setAttribute("stroke-dashoffset", segmentArcLength);
        }
        return ring;
    }
    
    const redDouble = createSegmentedRing(doubleRadius, redColor, true);
    const greenDouble = createSegmentedRing(doubleRadius, greenColor, false);
    const redTriple = createSegmentedRing(tripleRadius, redColor, true);
    const greenTriple = createSegmentedRing(tripleRadius, greenColor, false);

    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.setAttribute("transform", "rotate(-9)");
    g.appendChild(greenDouble);
    g.appendChild(redDouble);
    g.appendChild(greenTriple);
    g.appendChild(redTriple);
    svg.appendChild(g);

    const bullRadius = parseFloat(style.getPropertyValue('--bull-radius'));
    const bullseyeRadius = parseFloat(style.getPropertyValue('--bullseye-radius'));
    const outerBull = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    outerBull.setAttribute("r", bullRadius);
    outerBull.setAttribute("fill", style.getPropertyValue('--bull-color-outer').trim());
    const innerBull = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    innerBull.setAttribute("r", bullseyeRadius);
    innerBull.setAttribute("fill", style.getPropertyValue('--bull-color-inner').trim());
    svg.appendChild(outerBull);
    svg.appendChild(innerBull);

    if (mode === 'Double') {
        const doubleBlink = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        doubleBlink.setAttribute("r", doubleRadius);
        doubleBlink.setAttribute("fill", "none");
        doubleBlink.setAttribute("stroke", highlightColor);
        doubleBlink.setAttribute("stroke-width", strokeWidth + 0.5);
        doubleBlink.classList.add('blinking-overlay');
        svg.appendChild(doubleBlink);

        const bullseyeBlink = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        bullseyeBlink.setAttribute("r", bullseyeRadius);
        bullseyeBlink.setAttribute("fill", highlightColor);
        bullseyeBlink.classList.add('blinking-overlay');
        svg.appendChild(bullseyeBlink);
    } else if (mode === 'Triple') {
        const tripleBlink = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        tripleBlink.setAttribute("r", tripleRadius);
        tripleBlink.setAttribute("fill", "none");
        tripleBlink.setAttribute("stroke", highlightColor);
        tripleBlink.setAttribute("stroke-width", strokeWidth + 0.5);
        tripleBlink.classList.add('blinking-overlay');
        svg.appendChild(tripleBlink);
    }
    
    UI.focusSegmentGraphic.append(svg);
}