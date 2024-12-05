// Common utility functions for AFPD

// Function to format coordinates
function formatCoordinate(value, isLatitude) {
    const direction = isLatitude ? (value >= 0 ? 'N' : 'S') : (value >= 0 ? 'E' : 'W');
    const absValue = Math.abs(value);
    return `${absValue.toFixed(6)}° ${direction}`;
}

// Function to format altitude
function formatAltitude(value) {
    return value ? `${value.toLocaleString()} ft` : 'Not specified';
}

// Function to format speed
function formatSpeed(value) {
    return value ? `${value} kts` : 'Not specified';
}

// Function to chain waypoints with terrain analysis
async function chainWaypoints(procedureId) {
    try {
        const response = await fetch(`/api/chain?procedure_id=${procedureId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error chaining waypoints:', error);
        throw error;
    }
}

// Function to validate coordinates
function validateCoordinates(lat, lon) {
    return lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180;
}

// Function to calculate distance between two points (in nautical miles)
function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 3440.065; // Earth's radius in nautical miles
    const φ1 = lat1 * Math.PI / 180;
    const φ2 = lat2 * Math.PI / 180;
    const Δφ = (lat2 - lat1) * Math.PI / 180;
    const Δλ = (lon2 - lon1) * Math.PI / 180;

    const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
            Math.cos(φ1) * Math.cos(φ2) *
            Math.sin(Δλ/2) * Math.sin(Δλ/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));

    return R * c;
}

// Function to format procedure type
function formatProcedureType(type) {
    return type.replace('_', ' ').toLowerCase()
        .replace(/\b\w/g, l => l.toUpperCase());
}

// Function to show error message
function showError(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-danger alert-dismissible fade show';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.querySelector('main').insertBefore(alertDiv, document.querySelector('main').firstChild);
}

// Function to show success message
function showSuccess(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-success alert-dismissible fade show';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.querySelector('main').insertBefore(alertDiv, document.querySelector('main').firstChild);
}

// Export functions if using modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        formatCoordinate,
        formatAltitude,
        formatSpeed,
        chainWaypoints,
        validateCoordinates,
        calculateDistance,
        formatProcedureType,
        showError,
        showSuccess
    };
} 