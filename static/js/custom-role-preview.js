
// Enhanced Custom Role Preview Script
class CustomRolePreview {
    constructor() {
        this.previewElement = document.getElementById('preview-text');
        this.previewEmoji = document.getElementById('preview-emoji');
        this.initEventListeners();
        this.updatePreview();
    }

    initEventListeners() {
        // Role name
        document.getElementById('custom_role')?.addEventListener('input', (e) => {
            this.updatePreviewText(e.target.value || 'Моя роль');
        });

        // Emoji
        document.getElementById('custom_role_emoji')?.addEventListener('input', (e) => {
            this.updatePreviewEmoji(e.target.value || '🌟');
        });

        // Color
        document.getElementById('custom_role_color')?.addEventListener('input', (e) => {
            this.updatePreview();
        });

        // Gradient controls
        document.getElementById('use_gradient')?.addEventListener('change', (e) => {
            this.toggleGradientControls(e.target.checked);
            this.updatePreview();
        });

        document.getElementById('gradient_start')?.addEventListener('input', () => this.updatePreview());
        document.getElementById('gradient_end')?.addEventListener('input', () => this.updatePreview());

        // Animation
        document.getElementById('animated_gradient')?.addEventListener('change', (e) => {
            this.toggleAnimationControls(e.target.checked);
            this.updatePreview();
        });

        document.getElementById('animation_speed')?.addEventListener('change', () => this.updatePreview());

        // Effects
        document.getElementById('custom_role_glow')?.addEventListener('change', (e) => {
            this.toggleGlowControls(e.target.checked);
            this.updatePreview();
        });

        document.getElementById('custom_role_glow_color')?.addEventListener('input', () => this.updatePreview());

        document.getElementById('custom_role_shadow')?.addEventListener('change', (e) => {
            this.toggleShadowControls(e.target.checked);
            this.updatePreview();
        });

        document.getElementById('custom_role_shadow_color')?.addEventListener('input', () => this.updatePreview());

        // Border
        document.getElementById('custom_role_border')?.addEventListener('change', (e) => {
            this.toggleBorderControls(e.target.checked);
            this.updatePreview();
        });

        document.getElementById('custom_role_border_color')?.addEventListener('input', () => this.updatePreview());

        // Background
        document.getElementById('custom_role_background')?.addEventListener('input', () => this.updatePreview());

        // Font styling
        document.getElementById('custom_role_font_weight')?.addEventListener('change', () => this.updatePreview());
        document.getElementById('custom_role_font_style')?.addEventListener('change', () => this.updatePreview());
        document.getElementById('custom_role_text_transform')?.addEventListener('change', () => this.updatePreview());
    }

    toggleGradientControls(show) {
        const controls = document.querySelector('.gradient-controls');
        if (controls) {
            controls.style.display = show ? 'block' : 'none';
        }
    }

    toggleAnimationControls(show) {
        const controls = document.querySelector('.animation-controls');
        if (controls) {
            controls.style.display = show ? 'block' : 'none';
        }
    }

    toggleGlowControls(show) {
        const controls = document.querySelector('.glow-controls');
        if (controls) {
            controls.style.display = show ? 'block' : 'none';
        }
    }

    toggleShadowControls(show) {
        const controls = document.querySelector('.shadow-controls');
        if (controls) {
            controls.style.display = show ? 'block' : 'none';
        }
    }

    toggleBorderControls(show) {
        const controls = document.querySelector('.border-controls');
        if (controls) {
            controls.style.display = show ? 'block' : 'none';
        }
    }

    updatePreviewText(text) {
        if (this.previewElement) {
            this.previewElement.textContent = text;
        }
    }

    updatePreviewEmoji(emoji) {
        if (this.previewEmoji) {
            this.previewEmoji.textContent = emoji;
        }
    }

    updatePreview() {
        if (!this.previewElement) return;

        const styles = [];
        const classes = ['preview-role-text'];

        // Basic color
        const color = document.getElementById('custom_role_color')?.value || '#ffd700';
        
        // Gradient
        const useGradient = document.getElementById('use_gradient')?.checked;
        if (useGradient) {
            const startColor = document.getElementById('gradient_start')?.value || '#ff6b35';
            const endColor = document.getElementById('gradient_end')?.value || '#f7931e';
            styles.push(`background: linear-gradient(45deg, ${startColor}, ${endColor})`);
            styles.push('background-size: 200% 200%');
            styles.push('-webkit-background-clip: text');
            styles.push('-webkit-text-fill-color: transparent');
            styles.push('background-clip: text');
            classes.push('gradient-text');
        } else {
            styles.push(`color: ${color}`);
        }

        // Background
        const backgroundColor = document.getElementById('custom_role_background')?.value;
        if (backgroundColor && backgroundColor !== '#000000') {
            styles.push(`background-color: ${backgroundColor}`);
            styles.push('padding: 4px 8px');
            styles.push('border-radius: 4px');
            styles.push('display: inline-block');
        }

        // Glow effect
        const hasGlow = document.getElementById('custom_role_glow')?.checked;
        if (hasGlow) {
            const glowColor = document.getElementById('custom_role_glow_color')?.value || '#ffd700';
            styles.push(`text-shadow: 0 0 10px ${glowColor}, 0 0 20px ${glowColor}, 0 0 30px ${glowColor}`);
            classes.push('glow-effect');
        }

        // Shadow
        const hasShadow = document.getElementById('custom_role_shadow')?.checked;
        if (hasShadow) {
            const shadowColor = document.getElementById('custom_role_shadow_color')?.value || '#000000';
            const existingShadow = styles.find(s => s.startsWith('text-shadow'));
            if (existingShadow) {
                // Combine with existing glow
                const shadowIndex = styles.findIndex(s => s.startsWith('text-shadow'));
                styles[shadowIndex] += `, 2px 2px 4px ${shadowColor}`;
            } else {
                styles.push(`text-shadow: 2px 2px 4px ${shadowColor}`);
            }
        }

        // Border
        const hasBorder = document.getElementById('custom_role_border')?.checked;
        if (hasBorder) {
            const borderColor = document.getElementById('custom_role_border_color')?.value || '#ffd700';
            styles.push(`border: 1px solid ${borderColor}`);
            styles.push('padding: 2px 6px');
            styles.push('border-radius: 4px');
            styles.push('display: inline-block');
        }

        // Font styling
        const fontWeight = document.getElementById('custom_role_font_weight')?.value || 'bold';
        const fontStyle = document.getElementById('custom_role_font_style')?.value || 'normal';
        const textTransform = document.getElementById('custom_role_text_transform')?.value || 'none';
        
        styles.push(`font-weight: ${fontWeight}`);
        styles.push(`font-style: ${fontStyle}`);
        styles.push(`text-transform: ${textTransform}`);

        // Animation
        const isAnimated = document.getElementById('animated_gradient')?.checked;
        if (isAnimated) {
            const speed = document.getElementById('animation_speed')?.value || '3s';
            styles.push(`animation: gradientShift ${speed} ease-in-out infinite`);
            classes.push('animated-role');
        }

        // Apply styles
        this.previewElement.style.cssText = styles.join('; ');
        this.previewElement.className = classes.join(' ');
    }
}

// Initialize preview when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('preview-text')) {
        new CustomRolePreview();
    }
});
