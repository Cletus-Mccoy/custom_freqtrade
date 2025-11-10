export class PairChipsManager {
    constructor(options = {}) {
        this.containerId = options.containerId || 'pairChipsContainer';
        this.warningId = options.warningId || 'pairlistDuplicateWarning';
        this.container = document.getElementById(this.containerId);
        this.pairs = [];
        this.editable = false;
        this.onChange = options.onChange || (() => {});
    }

    setPairs(pairs, editable = false) {
        this.pairs = [...pairs];
        this.editable = editable;
        this.render();
    }

    setEditable(editable) {
        this.editable = editable;
        this.render();
    }

    addPair(pair) {
        if (!this.pairs.includes(pair)) {
            this.pairs.push(pair);
            this.render();
            this.onChange(this.pairs);
            return true;
        }
        return false;
    }

    removePair(index) {
        this.pairs.splice(index, 1);
        this.render();
        this.onChange(this.pairs);
    }

    getPairs() {
        return [...this.pairs];
    }

    render() {
        if (!this.container) return;
        
        this.container.innerHTML = '';
        const seen = new Set();
        let hasDuplicates = false;

        this.pairs.forEach((pair, idx) => {
            const chip = document.createElement('span');
            chip.className = 'badge d-flex align-items-center ' + 
                           (seen.has(pair) ? 'bg-danger' : 'bg-primary');
            chip.style.marginRight = '6px';
            chip.textContent = pair;

            if (seen.has(pair)) hasDuplicates = true;
            seen.add(pair);

            if (this.editable) {
                const closeBtn = document.createElement('button');
                closeBtn.type = 'button';
                closeBtn.className = 'btn-close btn-close-white btn-sm ms-2';
                closeBtn.style.fontSize = '0.7em';
                closeBtn.onclick = () => this.removePair(idx);
                chip.appendChild(closeBtn);
            }

            this.container.appendChild(chip);
        });

        // Update warning message
        let warn = document.getElementById(this.warningId);
        if (!warn) {
            warn = document.createElement('div');
            warn.id = this.warningId;
            warn.className = 'text-danger small mt-2';
            this.container.parentNode.appendChild(warn);
        }
        warn.style.display = hasDuplicates ? '' : 'none';
        warn.textContent = hasDuplicates ? 
            'Duplicate pairs detected! Duplicates are highlighted in red.' : '';
    }
}